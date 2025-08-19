import os
import shutil
import zipfile
import tempfile
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.models import Attachment, Schedule, User, ScheduleShare
from app.schemas.schemas import Attachment as AttachmentSchema
from app.core.auth import get_current_active_user
from pathlib import Path
from pydantic import BaseModel
import datetime

router = APIRouter()

# 업로드 디렉토리 생성
UPLOAD_DIR = Path("./static/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 파일 이름 변경을 위한 스키마
class FileRenameRequest(BaseModel):
    filename: str

# 다중 파일 작업을 위한 스키마
class MultiFileRequest(BaseModel):
    file_ids: List[int]

@router.get("/", response_model=List[AttachmentSchema])
async def get_all_attachments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """모든 첨부파일을 조회합니다."""
    # 사용자가 볼 수 있는 첨부파일만 반환 (공개 일정 + 본인 일정 + 공유받은 일정)
    attachments = db.query(Attachment).options(
        joinedload(Attachment.uploader),
        joinedload(Attachment.schedule)
    ).join(Schedule).filter(
        # 개인일정이 아니거나 본인이 작성한 일정
        (Schedule.individual == False) | (Schedule.owner_id == current_user.id)
    ).all()
    
    # schedule_title과 project_name을 첨부파일 객체에 추가
    for attachment in attachments:
        if hasattr(attachment, 'schedule') and attachment.schedule:
            attachment.schedule_title = attachment.schedule.title
            attachment.project_name = attachment.schedule.project_name
    
    return attachments

@router.get("/search", response_model=List[AttachmentSchema])
async def search_attachments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    filename_pattern: Optional[str] = Query(None),
    uploader_id: Optional[int] = Query(None),
    project_name: Optional[str] = Query(None),
    schedule_title: Optional[str] = Query(None)
):
    """필터를 이용하여 첨부파일을 검색합니다."""
    
    query = db.query(Attachment).options(
        joinedload(Attachment.uploader),
        joinedload(Attachment.schedule)
    ).join(Schedule).filter(
        # 개인일정이 아니거나 본인이 작성한 일정
        (Schedule.individual == False) | (Schedule.owner_id == current_user.id)
    )
    
    # 날짜 필터
    if start_date:
        try:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Attachment.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Attachment.created_at <= end_dt)
        except ValueError:
            pass
    
    # 파일명 패턴 필터
    if filename_pattern:
        if '*' in filename_pattern:
            # 와일드카드 패턴 지원
            pattern = filename_pattern.replace('*', '%')
            query = query.filter(Attachment.filename.ilike(pattern))
        else:
            # 부분 매칭
            query = query.filter(Attachment.filename.ilike(f'%{filename_pattern}%'))
    
    # 업로더 필터
    if uploader_id:
        query = query.filter(Attachment.uploader_id == uploader_id)
    
    # 프로젝트명 필터
    if project_name:
        query = query.filter(Schedule.project_name.ilike(f'%{project_name}%'))
    
    # 일정 제목 필터
    if schedule_title:
        query = query.filter(Schedule.title.ilike(f'%{schedule_title}%'))
    
    # 생성일 기준 내림차순 정렬
    attachments = query.order_by(Attachment.created_at.desc()).all()
    
    # schedule_title과 project_name을 첨부파일 객체에 추가
    for attachment in attachments:
        if hasattr(attachment, 'schedule') and attachment.schedule:
            attachment.schedule_title = attachment.schedule.title
            attachment.project_name = attachment.schedule.project_name
    
    return attachments

@router.post("/schedules/{schedule_id}/attachments")
async def upload_files_to_schedule(
    schedule_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # 일정 존재 여부 확인
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # 업로드된 파일들 저장
    uploaded_files = []
    for file in files:
        # 파일명 안전화 및 중복 방지
        safe_filename = f"{schedule_id}_{file.filename}"
        file_path = UPLOAD_DIR / safe_filename
        
        # 중복 파일명 처리
        counter = 1
        original_path = file_path
        while file_path.exists():
            name, ext = original_path.stem, original_path.suffix
            file_path = UPLOAD_DIR / f"{name}_{counter}{ext}"
            counter += 1
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # DB에 첨부파일 정보 저장
        attachment = Attachment(
            filename=file.filename,
            file_path=f"/static/uploads/{file_path.name}",
            file_size=file_path.stat().st_size,
            mime_type=file.content_type,
            schedule_id=schedule_id,
            uploader_id=current_user.id,
            created_at=datetime.datetime.now()
        )
        db.add(attachment)
        uploaded_files.append(attachment)
    
    db.commit()
    return {"message": f"{len(uploaded_files)} files uploaded successfully", "files": uploaded_files}

@router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # 권한 확인 (업로더 본인이거나 일정 소유자)
    schedule = db.query(Schedule).filter(Schedule.id == attachment.schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Related schedule not found")
    
    if attachment.uploader_id != current_user.id and schedule.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 파일 시스템에서 파일 삭제
    file_path = Path("." + attachment.file_path)  # /uploads/filename -> ./uploads/filename
    if file_path.exists():
        file_path.unlink()
    
    # DB에서 삭제
    db.delete(attachment)
    db.commit()
    
    return {"message": "Attachment deleted successfully"}

@router.put("/{attachment_id}/rename")
async def rename_attachment(
    attachment_id: int,
    request: FileRenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """첨부파일 이름을 변경합니다."""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # 권한 확인 (업로더 본인이거나 일정 소유자)
    schedule = db.query(Schedule).filter(Schedule.id == attachment.schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Related schedule not found")
    
    if attachment.uploader_id != current_user.id and schedule.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 파일명 업데이트
    attachment.filename = request.filename
    db.commit()
    
    return {"message": "Filename updated successfully", "filename": request.filename}

@router.post("/download/zip")
async def download_multiple_files(
    request: MultiFileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """선택된 여러 파일을 ZIP으로 압축하여 다운로드합니다."""
    
    # 파일들 조회 및 권한 확인
    attachments = []
    for file_id in request.file_ids:
        attachment = db.query(Attachment).filter(Attachment.id == file_id).first()
        if not attachment:
            continue
        
        # 권한 확인
        schedule = db.query(Schedule).filter(Schedule.id == attachment.schedule_id).first()
        if schedule and ((not schedule.individual) or (schedule.owner_id == current_user.id)):
            attachments.append(attachment)
    
    if not attachments:
        raise HTTPException(status_code=404, detail="No accessible files found")
    
    # 임시 ZIP 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
        with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for attachment in attachments:
                file_path = Path("." + attachment.file_path)
                if file_path.exists():
                    # 같은 이름 파일이 있을 경우 번호 추가
                    archive_name = attachment.filename
                    counter = 1
                    while archive_name in [info.filename for info in zipf.filelist]:
                        name, ext = Path(attachment.filename).stem, Path(attachment.filename).suffix
                        archive_name = f"{name}_{counter}{ext}"
                        counter += 1
                    
                    zipf.write(file_path, archive_name)
        
        # ZIP 파일 다운로드 응답
        return FileResponse(
            tmp_zip.name,
            media_type='application/zip',
            filename=f"attachments_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )

@router.delete("/delete/batch")
async def delete_multiple_files(
    request: MultiFileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """선택된 여러 파일을 일괄 삭제합니다."""
    
    deleted_count = 0
    for file_id in request.file_ids:
        attachment = db.query(Attachment).filter(Attachment.id == file_id).first()
        if not attachment:
            continue
        
        # 권한 확인
        schedule = db.query(Schedule).filter(Schedule.id == attachment.schedule_id).first()
        if not schedule:
            continue
        
        if attachment.uploader_id != current_user.id and schedule.owner_id != current_user.id:
            continue
        
        # 파일 시스템에서 삭제
        file_path = Path("." + attachment.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass  # 파일 삭제 실패해도 DB에서는 삭제
        
        # DB에서 삭제
        db.delete(attachment)
        deleted_count += 1
    
    db.commit()
    
    return {"message": f"{deleted_count} files deleted successfully"}