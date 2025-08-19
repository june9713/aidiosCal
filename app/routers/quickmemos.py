from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import QuickMemo, User
from app.schemas.schemas import QuickMemoCreate, QuickMemo as QuickMemoSchema, QuickMemoUpdate

router = APIRouter(
    prefix="/api/quickmemos",
    tags=["quickmemos"]
)

@router.post("", response_model=QuickMemoSchema)
async def create_quickmemo(
    quickmemo: QuickMemoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """새 퀵메모를 생성합니다."""
    db_quickmemo = QuickMemo(
        content=quickmemo.content,
        author_id=current_user.id,
        created_at=datetime.now()
    )
    db.add(db_quickmemo)
    db.commit()
    db.refresh(db_quickmemo)
    return db_quickmemo

@router.get("", response_model=List[QuickMemoSchema])
async def get_quickmemos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """사용자의 퀵메모 목록을 조회합니다 (삭제되지 않은 것만)."""
    quickmemos = db.query(QuickMemo).filter(
        QuickMemo.author_id == current_user.id,
        QuickMemo.is_deleted == False
    ).order_by(QuickMemo.created_at.desc()).offset(skip).limit(limit).all()
    return quickmemos

@router.put("/{quickmemo_id}/complete", response_model=QuickMemoSchema)
async def toggle_quickmemo_complete(
    quickmemo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """퀵메모의 완료 상태를 토글합니다."""
    db_quickmemo = db.query(QuickMemo).filter(
        QuickMemo.id == quickmemo_id,
        QuickMemo.author_id == current_user.id,
        QuickMemo.is_deleted == False
    ).first()
    
    if not db_quickmemo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="퀵메모를 찾을 수 없습니다."
        )
    
    db_quickmemo.is_completed = not db_quickmemo.is_completed
    db.commit()
    db.refresh(db_quickmemo)
    return db_quickmemo

@router.delete("/{quickmemo_id}")
async def delete_quickmemo(
    quickmemo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """퀵메모를 소프트 삭제합니다."""
    db_quickmemo = db.query(QuickMemo).filter(
        QuickMemo.id == quickmemo_id,
        QuickMemo.author_id == current_user.id,
        QuickMemo.is_deleted == False
    ).first()
    
    if not db_quickmemo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="퀵메모를 찾을 수 없습니다."
        )
    
    db_quickmemo.is_deleted = True
    db.commit()
    return {"message": "퀵메모가 삭제되었습니다."}

@router.put("/{quickmemo_id}", response_model=QuickMemoSchema)
async def update_quickmemo(
    quickmemo_id: int,
    quickmemo_update: QuickMemoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """퀵메모를 수정합니다."""
    db_quickmemo = db.query(QuickMemo).filter(
        QuickMemo.id == quickmemo_id,
        QuickMemo.author_id == current_user.id,
        QuickMemo.is_deleted == False
    ).first()
    
    if not db_quickmemo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="퀵메모를 찾을 수 없습니다."
        )
    
    update_data = quickmemo_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_quickmemo, field, value)
    
    db.commit()
    db.refresh(db_quickmemo)
    return db_quickmemo 