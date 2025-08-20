from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
import os
from sqlalchemy import or_, and_, not_, func
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.models import User, Schedule, ScheduleShare, Attachment, PriorityLevel, Alarm, AlarmType
from app.schemas.schemas import (
    ScheduleCreate,
    Schedule as ScheduleSchema,
    ScheduleShareCreate,
    ScheduleShare as ScheduleShareSchema,
    Attachment as AttachmentSchema
)
from pydantic import BaseModel
from app.routers.auth import get_current_user
import logging
import sys
import pandas as pd
from fastapi.responses import StreamingResponse
import io
from datetime import datetime

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 콘솔 핸들러 추가
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# 로그 포맷 설정 - 더 상세한 정보 포함
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s:%(lineno)d - %(message)s'
)
console_handler.setFormatter(formatter)

# 핸들러 추가
logger.addHandler(console_handler)

# 추가: 루트 로거에도 핸들러 추가
root_logger = logging.getLogger()
if not root_logger.handlers:
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setLevel(logging.DEBUG)
    root_handler.setFormatter(formatter)
    root_logger.addHandler(root_handler)
    root_logger.setLevel(logging.DEBUG)

#print("🔧 [LOGGING_SETUP] Schedules router logging configured successfully!")
##print("🔧 [LOGGING_SETUP] Root logger also configured for comprehensive logging!")

router = APIRouter()

class MemoUpdate(BaseModel):
    memo: str

@router.post("/", response_model=ScheduleSchema)
def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    #print(f"🚀 [ENTRY_POINT] create_schedule 함수 진입 - 사용자: {current_user.username} (ID: {current_user.id})")
    #print(f"🚀 [ENTRY_POINT] 요청 데이터 타입: {type(schedule)}")
   # print(f"🚀 [ENTRY_POINT] 요청 데이터 내용: {schedule}")
    
    # 🔍 추가: 요청 데이터 전체를 문자열로 출력
    #print("🔍 [RAW_DATA] === 요청 데이터 전체 문자열 출력 ===")
    #print(f"🔍 [RAW_DATA] schedule.__dict__: {schedule.__dict__}")
    #print(f"🔍 [RAW_DATA] schedule.model_dump(): {schedule.model_dump()}")
    #print(f"🔍 [RAW_DATA] schedule.model_dump_json(): {schedule.model_dump_json()}")
    #print("🔍 [RAW_DATA] ======================================")
    
    try:
        # 1단계: 데이터 변환 및 검증
        #print("📋 [STEP_1] schedule.dict() 호출 시작...")
        schedule_data = schedule.dict()
        #print(f"📋 [STEP_1] 변환된 데이터: {schedule_data}")
       # print(f"📋 [STEP_1] 데이터 타입: {type(schedule_data)}")
       # print(f"📋 [STEP_1] 데이터 키들: {list(schedule_data.keys())}")
        
        # 공동 작업자 정보 추출
        #print("👥 [STEP_1] 공동작업자 정보 추출 시작...")
        collaborators = schedule_data.pop('collaborators', [])
        #print(f"👥 [STEP_1] 추출된 공동작업자: {collaborators}")
        #print(f"👥 [STEP_1] 공동작업자 타입: {type(collaborators)}")
        #print(f"👥 [STEP_1] 공동작업자 개수: {len(collaborators) if collaborators else 0}")
        
        # 🔍 추가: collaborators 필드가 원본 데이터에 있었는지 확인
        #print(f"🔍 [COLLAB_CHECK] 원본 schedule_data에 'collaborators' 키가 있었나요? {'collaborators' in schedule_data}")
        #print(f"🔍 [COLLAB_CHECK] 원본 schedule_data의 모든 키: {list(schedule_data.keys())}")
        
        #if collaborators:
            #print(f"👥 [STEP_1] 공동작업자 상세 분석:")
            #for i, collab_id in enumerate(collaborators):
                #print(f"   - 공동작업자 {i+1}: ID={collab_id}, 타입={type(collab_id)}")
         #       pass
         #       if collab_id == current_user.id:
                    #print(f"   ⚠️ 경고: 자기 자신을 공동작업자로 선택함 (ID: {collab_id})")
         #           pass
        #else:
         #   pass
            #print("⚠️ [COLLAB_WARNING] collaborators 배열이 비어있습니다!")
            #print("⚠️ [COLLAB_WARNING] 이는 다음 중 하나일 수 있습니다:")
            #print("   1. 프론트엔드에서 collaborators를 전송하지 않음")
            #print("   2. Pydantic 모델에서 collaborators 필드가 누락됨")
            #print("   3. 데이터 직렬화 과정에서 문제 발생")
        
        # 2단계: parent_order 계산
        #print("👨‍👦 [STEP_2] parent_order 계산 시작...")
        if schedule_data.get("parent_id"):
            #print(f"👨‍👦 [STEP_2] 부모 ID 발견: {schedule_data['parent_id']}")
            parent_schedule = db.query(Schedule).filter(Schedule.id == schedule_data["parent_id"]).first()
            if parent_schedule:
                parent_order = parent_schedule.parent_order
                #print(f"👨‍👦 [STEP_2] 부모의 parent_order: {parent_order}")
                max_order = db.query(func.max(Schedule.parent_order)).filter(
                    Schedule.parent_id == schedule_data["parent_id"]
                ).scalar() or parent_order
                #print(f"👨‍👦 [STEP_2] 최대 parent_order: {max_order}")
                schedule_data["parent_order"] = max_order + 1
                #print(f"👨‍👦 [STEP_2] 새 parent_order 설정: {schedule_data['parent_order']}")
            else:
                #print(f"⚠️ [STEP_2] 부모 일정을 찾을 수 없음: {schedule_data['parent_id']}")
                schedule_data["parent_order"] = 0
        else:
            #print("👨‍👦 [STEP_2] 부모 ID 없음, parent_order를 0으로 설정")
            schedule_data["parent_order"] = 0
        
        # 3단계: Schedule 객체 생성
        #print("📝 [STEP_3] Schedule 객체 생성 시작...")
        #print(f"📝 [STEP_3] 최종 schedule_data: {schedule_data}")
        #print(f"📝 [STEP_3] owner_id: {current_user.id}")
        
        db_schedule = Schedule(**schedule_data, owner_id=current_user.id)
        #print(f"📝 [STEP_3] Schedule 객체 생성 완료: {db_schedule}")
        #print(f"📝 [STEP_3] Schedule 객체 속성들: {dir(db_schedule)}")
        #print(f"📝 [STEP_3] Schedule 객체 __dict__: {db_schedule.__dict__}")
        
        # 4단계: DB에 일정 저장
        #print("💾 [STEP_4] 데이터베이스 저장 시작...")
        #print(f"💾 [STEP_4] db.add() 호출 전...")
        db.add(db_schedule)
        #print(f"💾 [STEP_4] db.add() 완료, db.commit() 호출...")
        db.commit()
        #print(f"💾 [STEP_4] db.commit() 완료!")
        #print(f"💾 [STEP_4] 저장된 일정 ID: {db_schedule.id}")
        
        # 5단계: DB에서 새로고침
        #print("🔄 [STEP_5] 데이터베이스에서 새로고침...")
        db.refresh(db_schedule)
        #print(f"🔄 [STEP_5] 새로고침 완료: {db_schedule}")
        #print(f"🔄 [STEP_5] 새로고침 후 ID: {db_schedule.id}")
        
        # 6단계: 공동 작업자 처리
        if collaborators:
            #print(f"👥 [STEP_6] 공동작업자 처리 시작 - {len(collaborators)}명...")
            added_collaborators = []
            skipped_collaborators = []
            
            for i, collaborator_id in enumerate(collaborators):
                #print(f"👥 [STEP_6] 공동작업자 {i+1} 처리 중: ID {collaborator_id}")
                
                if collaborator_id == current_user.id:
                    #print(f"⚠️ [STEP_6] 자기 자신은 공동작업자로 추가하지 않음: {collaborator_id}")
                    skipped_collaborators.append(collaborator_id)
                    continue
                
                # 사용자 존재 여부 확인
                #print(f"👥 [STEP_6] 사용자 ID {collaborator_id} 존재 여부 확인...")
                user_exists = db.query(User).filter(User.id == collaborator_id).first()
                if not user_exists:
                    #print(f"❌ [STEP_6] 사용자 ID {collaborator_id}를 찾을 수 없음, 건너뜀")
                    skipped_collaborators.append(collaborator_id)
                    continue
                
                #print(f"✅ [STEP_6] 사용자 ID {collaborator_id} 확인됨: {user_exists.username}")
                
                # ScheduleShare 객체 생성
                #print(f"👥 [STEP_6] ScheduleShare 객체 생성 중...")
                schedule_share = ScheduleShare(
                    schedule_id=db_schedule.id,
                    shared_with_id=collaborator_id,
                    role="collaborator",
                    can_edit=True,
                    can_delete=True,
                    can_complete=True,
                    can_share=True
                )
                #print(f"👥 [STEP_6] ScheduleShare 객체 생성 완료: {schedule_share}")
                #print(f"👥 [STEP_6] ScheduleShare 객체 속성: {schedule_share.__dict__}")
                
                db.add(schedule_share)
                added_collaborators.append(collaborator_id)
                #print(f"✅ [STEP_6] ScheduleShare 추가 완료: 사용자 ID {collaborator_id}")
            
            # ScheduleShare 변경사항 커밋
            if added_collaborators:
                #print(f"💾 [STEP_6] {len(added_collaborators)}개 ScheduleShare 레코드 커밋 중...")
                db.commit()
                #print(f"✅ [STEP_6] ScheduleShare 커밋 완료!")
                #print(f"✅ [STEP_6] 추가된 공동작업자: {added_collaborators}")
                #if skipped_collaborators:
                    #print(f"⚠️ [STEP_6] 건너뛴 공동작업자: {skipped_collaborators}")
                 #   pass
            else:
                pass#print("👥 [STEP_6] 추가할 공동작업자가 없음")
        else:
            pass#print("👥 [STEP_6] 공동작업자 없음, ScheduleShare 생성 건너뜀")
        
        # 7단계: 최종 결과 확인
        #print("🎯 [STEP_7] 최종 결과 확인 중...")
        db.refresh(db_schedule.owner)
        #print(f"🎯 [STEP_7] 소유자 정보: {db_schedule.owner.username} (ID: {db_schedule.owner.id})")
        
        # ScheduleShare 테이블에서 최종 확인
        #print("🔍 [STEP_7] ScheduleShare 테이블 최종 확인...")
        final_shares = db.query(ScheduleShare).filter(ScheduleShare.schedule_id == db_schedule.id).all()
        #print(f"🔍 [STEP_7] 최종 ScheduleShare 레코드 수: {len(final_shares)}")
        
        #for i, share in enumerate(final_shares):
        #    print(f"🔍 [STEP_7] Share {i+1}: ID={share.id}, Schedule={share.schedule_id}, User={share.shared_with_id}")
        
        # 8단계: 응답 데이터 구성
        #print("📤 [STEP_8] 응답 데이터 구성 중...")
        #print(f"📤 [STEP_8] 최종 db_schedule: {db_schedule}")
        #print(f"📤 [STEP_8] 응답 모델 타입: {ScheduleSchema}")
        
        #print("🎉 [FINAL] 일정 생성 완료! 응답 반환 중...")
        return db_schedule
        
    except Exception as e:
        print(f"❌ [ERROR] 오류 발생: {str(e)}")
        print(f"❌ [ERROR] 오류 타입: {type(e).__name__}")
        import traceback
        print(f"❌ [ERROR] 전체 스택 트레이스:")
        traceback.print_exc()
        
        logger.error(f"❌ [SCHEDULE_CREATE] Error creating schedule: {str(e)}")
        logger.error(f"❌ [SCHEDULE_CREATE] Error type: {type(e).__name__}")
        logger.error(f"❌ [SCHEDULE_CREATE] Full traceback: {traceback.format_exc()}")
        
        db.rollback()
        print("🔄 [ERROR] 데이터베이스 롤백 완료")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create schedule: {str(e)}"
        )

@router.get("/", response_model=List[ScheduleSchema])
def read_schedules(
    skip: int = 0,
    limit: int = 100,
    show_completed: bool = True,
    show_all_users: bool = True,
    completed_only: bool = False,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search_terms: Optional[str] = None,
    exclude_terms: Optional[str] = None,
    search_in_title: bool = True,
    search_in_content: bool = True,
    search_in_memo: bool = True,
    user_ids: Optional[List[int]] = Query(None),  # 사용자 ID 리스트 추가
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """일정 목록을 반환합니다."""
    #print(f"🔍 [DEBUG] read_schedules 시작 - user_ids: {user_ids}, show_all_users: {show_all_users}")
    #print(f"🔍 [DEBUG] 현재 사용자: {current_user.username} (ID: {current_user.id})")
    logger.info(f"read_schedules called - user_ids: {user_ids}, show_all_users: {show_all_users}")
    
    query = db.query(Schedule)

    # 삭제되지 않은 일정만 조회
    query = query.filter(Schedule.is_deleted == False)
    #print(f"🔍 [DEBUG] 삭제되지 않은 일정만 필터링 완료")

    # 사용자 및 개인일정 필터링
    #print(f"🔍 [DEBUG] 사용자 필터링 시작 - show_all_users: {show_all_users}")
    #print(f"🔍 [DEBUG] user_ids 파라미터: {user_ids}")
    #print(f"🔍 [DEBUG] 현재 사용자 ID: {current_user.id}")
    
    # 사용자 ID가 제공된 경우, show_all_users 값과 관계없이 선택된 사용자만 필터링
    if user_ids and len(user_ids) > 0:
        #print(f"🔍 [DEBUG] 사용자 ID 선택됨: {user_ids}")
        #print(f"🔍 [DEBUG] show_all_users 무시하고 선택된 사용자만 필터링")
        
        # 선택된 사용자가 공동작업자로 포함된 일정들 조회
        collaborator_schedules = db.query(ScheduleShare.schedule_id).filter(
            ScheduleShare.shared_with_id.in_(user_ids)
        ).all()
        collaborator_schedule_ids = [s[0] for s in collaborator_schedules]
#        print(f"🔍 [DEBUG] 선택된 사용자가 공동작업자로 포함된 일정 ID들: {collaborator_schedule_ids}")
        
        # 현재 사용자가 선택된 사용자 목록에 포함되어 있는지 확인
        current_user_in_selection = current_user.id in user_ids
        #print(f"🔍 [DEBUG] 현재 사용자({current_user.id})가 선택된 사용자 목록에 포함됨: {current_user_in_selection}")
        
        # 필터링 조건 구성
        filter_conditions = [
            Schedule.owner_id.in_(user_ids),  # 선택된 사용자가 소유한 일정 (개인일정 여부 상관없이)
            # 선택된 사용자가 공동작업자로 포함된 일정들
            Schedule.id.in_(collaborator_schedule_ids)
        ]
        
        # 현재 사용자가 선택된 사용자 목록에 포함되어 있는 경우에만 현재 사용자의 일정도 포함
        if current_user_in_selection:
            #print(f"🔍 [DEBUG] 현재 사용자의 일정도 포함하여 조회")
            filter_conditions.append(Schedule.owner_id == current_user.id)
        else:
            pass#print(f"🔍 [DEBUG] 현재 사용자의 일정은 제외하고 조회")
        
        query = query.filter(or_(*filter_conditions))
        #print(f"🔍 [DEBUG] 일반 사용자 필터링 조건 적용 완료")
        #print(f"🔍 [DEBUG] 최종 필터링 조건: owner_id IN {user_ids} OR schedule_id IN {collaborator_schedule_ids}")
    
    elif not show_all_users:
        # 자신의 일정만 조회
        #print(f"🔍 [DEBUG] 자신의 일정만 조회 모드")
        query = query.filter(Schedule.owner_id == current_user.id)
    else:
        # 모든 사용자 일정을 보되, 다른 사용자의 개인일정은 제외
        #print(f"🔍 [DEBUG] 모든 사용자 일정 조회 모드 (개인일정 제외)")
        query = query.filter(
            or_(
                Schedule.owner_id == current_user.id,  # 자신의 모든 일정
                and_(
                    Schedule.owner_id != current_user.id,  # 다른 사용자의 일정 중
                    Schedule.individual == False  # 개인일정이 아닌 것만
                )
            )
        )

    # 완료 상태 필터링
    if completed_only:
        query = query.filter(Schedule.is_completed == True)
    elif not show_completed:
        query = query.filter(Schedule.is_completed == False)

    # 날짜 범위 필터링
    if start_date:
        logger.info(f"[TIME_DEBUG] Filtering with start_date: {start_date}")
        query = query.filter(Schedule.date >= start_date)
    if end_date:
        logger.info(f"[TIME_DEBUG] Filtering with end_date: {end_date}")
        query = query.filter(Schedule.date <= end_date)

    # 검색어 필터링
    if search_terms:
        search_conditions = []
        for term in search_terms.split(','):
            term = term.strip()
            if term:
                term_conditions = []
                if search_in_title:
                    term_conditions.append(Schedule.title.ilike(f'%{term}%'))
                if search_in_content:
                    term_conditions.append(Schedule.content.ilike(f'%{term}%'))
                if search_in_memo:
                    term_conditions.append(Schedule.memo.ilike(f'%{term}%'))
                if term_conditions:
                    search_conditions.append(or_(*term_conditions))
        if search_conditions:
            query = query.filter(or_(*search_conditions))

    # 제외 검색어 필터링
    if exclude_terms:
        exclude_conditions = []
        for term in exclude_terms.split(','):
            term = term.strip()
            if term:
                exclude_term_conditions = []
                if search_in_title:
                    exclude_term_conditions.append(Schedule.title.ilike(f'%{term}%'))
                if search_in_content:
                    exclude_term_conditions.append(Schedule.content.ilike(f'%{term}%'))
                if search_in_memo:
                    exclude_term_conditions.append(Schedule.memo.ilike(f'%{term}%'))
                if exclude_term_conditions:
                    exclude_conditions.append(not_(or_(*exclude_term_conditions)))
        if exclude_conditions:
            query = query.filter(and_(*exclude_conditions))

    # 마감시간 기준 정렬
    query = query.order_by(
        Schedule.due_time.asc().nullslast(),
        Schedule.created_at.desc()
    )

    # shares 정보를 포함하여 로드
    query = query.options(
        joinedload(Schedule.owner),
        joinedload(Schedule.shares).joinedload(ScheduleShare.shared_with)
    )

    schedules = query.offset(skip).limit(limit).all()
    
    #print(f"🔍 [DEBUG] 최종 조회된 일정 수: {len(schedules)}")
    #print(f"🔍 [DEBUG] 조회된 일정들 상세:")
    
    # 모든 일정을 상세하게 출력
    for i, schedule in enumerate(schedules):
        owner_name = schedule.owner.username if schedule.owner else "Unknown"
        #print(f"   {i+1}. ID: {schedule.id}, 제목: '{schedule.title}', 소유자: {owner_name} (ID: {schedule.owner_id})")
        if hasattr(schedule, 'shares') and schedule.shares:
            collaborator_names = []
            for share in schedule.shares:
                if share.shared_with:
                    collaborator_names.append(f"{share.shared_with.username}(ID:{share.shared_with.id})")
                else:
                    collaborator_names.append(f"Unknown(ID:{share.shared_with_id})")
            #print(f"      공동작업자: {collaborator_names}")
        else:
            pass#print(f"      공동작업자: 없음")
    
    # 필터링 조건 검증을 위한 추가 로그
    if user_ids and len(user_ids) > 0:
        #print(f"🔍 [DEBUG] === 필터링 조건 검증 ===")
       # print(f"🔍 [DEBUG] 선택된 사용자 ID들: {user_ids}")
        
        # 선택된 사용자들의 이름 조회
        selected_users = db.query(User).filter(User.id.in_(user_ids)).all()
        selected_user_names = [f"{user.username}(ID:{user.id})" for user in selected_users]
        #print(f"🔍 [DEBUG] 선택된 사용자들: {selected_user_names}")
        
        # 각 일정이 왜 포함되었는지 분석
        for schedule in schedules:
            reason = []
            if schedule.owner_id in user_ids:
                reason.append(f"소유자({schedule.owner.username})가 선택됨")
            
            if hasattr(schedule, 'shares') and schedule.shares:
                for share in schedule.shares:
                    if share.shared_with_id in user_ids:
                        reason.append(f"공동작업자({share.shared_with.username})가 선택됨")
            
            #if reason:
            #    print(f"🔍 [DEBUG] 일정 '{schedule.title}' 포함 이유: {', '.join(reason)}")
            #else:
            #    print(f"🔍 [DEBUG] ⚠️ 일정 '{schedule.title}'이 포함된 이유를 찾을 수 없음!")
        
        #print(f"🔍 [DEBUG] === 필터링 조건 검증 완료 ===")
    
    logger.info(f"Returning {len(schedules)} schedules for user {current_user.id}")
    return schedules

@router.get("/{schedule_id}", response_model=ScheduleSchema)
def read_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        schedule = db.query(Schedule).filter(
            Schedule.id == schedule_id,
            Schedule.is_deleted == False,
            or_(
                Schedule.owner_id == current_user.id,  # 자신의 일정
                and_(
                    Schedule.owner_id != current_user.id,  # 다른 사용자의 일정 중
                    Schedule.individual == False  # 개인일정이 아닌 것만
                ),
                Schedule.id.in_(  # 또는 공유받은 일정
                    db.query(ScheduleShare.schedule_id)
                    .filter(
                        ScheduleShare.schedule_id == schedule_id,
                        ScheduleShare.shared_with_id == current_user.id
                    )
                )
            )
        ).options(
            joinedload(Schedule.owner),
            joinedload(Schedule.shares).joinedload(ScheduleShare.shared_with)
        ).first()
        
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        # 디버그 로깅 추가
        logger.info(f"Schedule {schedule_id} loaded with {len(schedule.shares) if schedule.shares else 0} shares")
        if schedule.shares:
            for share in schedule.shares:
                logger.info(f"Share: schedule_id={share.schedule_id}, shared_with_id={share.shared_with_id}")
        
        return schedule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch schedule: {str(e)}"
        )

@router.put("/{schedule_id}", response_model=ScheduleSchema)
def update_schedule(
    schedule_id: int,
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        # 권한 확인: 일정 소유자이거나 공동 작업자(수정 권한 있음)인지 확인
        from app.core.permissions import can_edit_schedule
        
        if not can_edit_schedule(db, current_user.id, schedule_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You don't have permission to edit this schedule"
            )
        
        db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if db_schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        # 공동 작업자 정보 제거 (Schedule 모델에 직접 저장되지 않음)
        schedule_data = schedule.dict()
        collaborators = schedule_data.pop('collaborators', [])
        
        # 일정 정보 업데이트
        for key, value in schedule_data.items():
            setattr(db_schedule, key, value)
        
        db.commit()
        db.refresh(db_schedule)
        
        # 기존 공동 작업자 정보 삭제
        db.query(ScheduleShare).filter(ScheduleShare.schedule_id == schedule_id).delete()
        
        # 새로운 공동 작업자 정보 저장
        if collaborators:
            for collaborator_id in collaborators:
                if collaborator_id != current_user.id:  # 자신은 공동 작업자로 추가하지 않음
                    schedule_share = ScheduleShare(
                        schedule_id=schedule_id,
                        shared_with_id=collaborator_id
                    )
                    db.add(schedule_share)
            
            db.commit()
            logger.info(f"Updated {len(collaborators)} collaborators for schedule {schedule_id}")
        
        db.refresh(db_schedule)
        return db_schedule
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update schedule: {str(e)}"
        )

@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """일정을 삭제합니다 (soft delete)."""
    # 권한 확인: 일정 소유자이거나 공동 작업자(삭제 권한 있음)인지 확인
    from app.core.permissions import can_delete_schedule
    
    if not can_delete_schedule(db, current_user.id, schedule_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You don't have permission to delete this schedule"
        )
    
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.is_deleted == False
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # 실제 삭제 대신 is_deleted 플래그를 True로 설정
    schedule.is_deleted = True
    
    # 연관된 알람들도 함께 soft delete 처리
    for alarm in schedule.alarms:
        alarm.is_deleted = True
    
    db.commit()
    return {"message": "Schedule deleted successfully"}

@router.post("/{schedule_id}/complete")
def complete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        # 권한 확인: 일정 소유자이거나 공동 작업자(완료 처리 권한 있음)인지 확인
        from app.core.permissions import can_complete_schedule
        
        if not can_complete_schedule(db, current_user.id, schedule_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You don't have permission to complete this schedule"
            )
        
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        schedule.is_completed = True
        db.commit()
        return {"message": "Schedule marked as completed"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to complete schedule: {str(e)}"
        )

@router.post("/{schedule_id}/share", response_model=ScheduleShareSchema)
def share_schedule(
    schedule_id: int,
    share: ScheduleShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        # 권한 확인: 일정 소유자이거나 공동 작업자(공유 권한 있음)인지 확인
        from app.core.permissions import can_share_schedule
        
        if not can_share_schedule(db, current_user.id, schedule_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You don't have permission to share this schedule"
            )
        
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        db_share = ScheduleShare(**share.dict())
        db.add(db_share)
        db.commit()
        db.refresh(db_share)
        return db_share
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to share schedule: {str(e)}"
        )

@router.put("/{schedule_id}/memo", response_model=ScheduleSchema)
async def update_schedule_memo(
    schedule_id: int,
    memo_update: MemoUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # 시작 로그
    #logger.info(f"[MEMO UPDATE START] Schedule ID: {schedule_id}, User: {current_user.name} (ID: {current_user.id})")
    #logger.debug(f"[MEMO DATA] Received memo data: {memo_update.dict()}")
    
    try:
        # 일정 조회
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            logger.error(f"[MEMO ERROR] Schedule not found: {schedule_id}")
            raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다")
        
        logger.info(f"[MEMO INFO] Schedule found - Title: '{schedule.title}', Owner: {schedule.owner_id}")
        logger.debug(f"[MEMO INFO] Previous memo: '{schedule.memo}'")
        
        # 메모 업데이트
        new_memo = memo_update.memo
        old_memo = schedule.memo
        
        # 메모가 실제로 변경되었는지 확인
        if new_memo == old_memo:
            logger.info(f"[MEMO SKIP] No changes detected in memo content")
            return schedule
            
        schedule.memo = new_memo
        schedule.memo_author_id = current_user.id
        schedule.memo_updated_at = datetime.now()
        
        logger.info(f"[MEMO UPDATE] Memo changed from '{old_memo}' to '{new_memo}'")
        
        # 알람 생성 로직
        alarm_created = False
        if schedule.owner_id != current_user.id:  
            # 다른 사용자가 메모를 추가한 경우
            logger.info(f"[ALARM CREATE] Creating memo alarm - Schedule owner: {schedule.owner_id}, Editor: {current_user.id}")
            
            if schedule.individual:
                # 개인일정: 소유자에게만 알림
                new_alarm = Alarm(
                    user_id=schedule.owner_id,  # 일정 소유자에게 알림
                    schedule_id=schedule_id,
                    type=AlarmType.MEMO,
                    message=f"{current_user.name}님이 일정 '{schedule.title}'에 메모를 추가했습니다."
                )
                db.add(new_alarm)
                alarm_created = True
                logger.info(f"[ALARM SUCCESS] Individual memo alarm created for user {schedule.owner_id}")
            else:
                # 일반일정: 모든 사용자에게 알림
                all_users = db.query(User).all()
                for user in all_users:
                    if user.id != current_user.id:  # 본인 제외
                        new_alarm = Alarm(
                            user_id=user.id,
                            schedule_id=schedule_id,
                            type=AlarmType.MEMO,
                            message=f"{current_user.name}님이 일정 '{schedule.title}'에 메모를 추가했습니다."
                        )
                        db.add(new_alarm)
                alarm_created = True
                logger.info(f"[ALARM SUCCESS] Public memo alarms created for all users")
        else:
            # 본인이 자신의 일정에 메모를 추가한 경우
            if not schedule.individual:
                # 일반일정의 경우 다른 모든 사용자에게 알림
                all_users = db.query(User).all()
                for user in all_users:
                    if user.id != current_user.id:  # 본인 제외
                        new_alarm = Alarm(
                            user_id=user.id,
                            schedule_id=schedule_id,
                            type=AlarmType.MEMO,
                            message=f"{current_user.name}님이 일정 '{schedule.title}'에 메모를 추가했습니다."
                        )
                        db.add(new_alarm)
                alarm_created = True
                logger.info(f"[ALARM SUCCESS] Public memo alarms created for all other users")
            else:
                # 개인일정의 경우 알림 없음
                logger.info(f"[ALARM SKIP] No alarm created - User editing own individual schedule")
        
        # 데이터베이스 커밋
        db.commit()
        logger.info(f"[MEMO SUCCESS] Database committed successfully")
        
        # 최종 결과 로그
        result = {
            "id": schedule.id,
            "title": schedule.title,
            "memo": schedule.memo
        }
        
        logger.info(f"[MEMO COMPLETE] Schedule: {schedule_id}, Alarm created: {alarm_created}")
        logger.debug(f"[MEMO RESULT] Final result: {result}")
        
        return schedule
        
    except HTTPException:
        # HTTPException은 그대로 전파
        raise
    except Exception as e:
        # 예상치 못한 오류 처리
        logger.error(f"[MEMO ERROR] Unexpected error in memo update: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="메모 업데이트 중 오류가 발생했습니다")

@router.get("/{schedule_id}/parent", response_model=ScheduleSchema)
async def get_schedule_parent(
    schedule_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """스케줄의 부모 작업을 반환합니다."""
    # 1. schedule_id로 스케줄을 찾음 (owner_id 조건 제거)
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if not schedule.parent_id:
        raise HTTPException(status_code=404, detail="Parent schedule not found")
    
    # 2. 부모 스케줄도 owner_id 조건 없이 조회
    parent = db.query(Schedule).filter(
        Schedule.id == schedule.parent_id
    ).first()
    
    if not parent:
        raise HTTPException(status_code=404, detail="Parent schedule not found")
    
    return parent

@router.get("/export/excel")
async def export_schedules_to_excel(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_individual: bool = False,
    export_by_project: bool = False,
    export_by_author: bool = False,
    export_by_month: bool = False,
    export_by_week: bool = False,
    export_by_priority: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        import zipfile
        import tempfile
        import os
        from collections import defaultdict
        
        # 모든 사용자와 일정 조회
        users = db.query(User).all()
        
        # 현재 시간
        now = datetime.now()
        
        # 기본 쿼리 생성 함수
        def create_base_query(user_id=None):
            query = db.query(Schedule)
            if user_id:
                query = query.filter(Schedule.owner_id == user_id)
            
            query = query.filter(Schedule.is_deleted == False)
            
            # 개인일정 포함 여부
            if not include_individual:
                query = query.filter(Schedule.individual == False)
            
            # 날짜 범위 필터
            if start_date and end_date:
                query = query.filter(Schedule.date >= start_date)
                query = query.filter(Schedule.date <= end_date)
            elif not start_date and not end_date:
                # 기본값: 미완료 일정만
                query = query.filter(Schedule.is_completed == False)
            
            return query.order_by(Schedule.date.asc())
        
        # 일정 데이터를 딕셔너리로 변환하는 함수
        def schedule_to_dict(schedule, user_name):
            return {
                '작성자': user_name,
                '완료여부': '완료' if schedule.is_completed else '미완료',
                '날짜': schedule.date,
                '마감시간': schedule.due_time,
                '프로젝트': schedule.project_name or '',
                '제목': schedule.title,
                '내용': schedule.content or '',
                '메모': schedule.memo or '',
                '우선순위': schedule.priority.value if schedule.priority else '',
                '개인일정': '예' if schedule.individual else '아니오'
            }
        
        # 스타일 정의 함수
        def create_formats(workbook):
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#4472C4',
                'font_color': '#FFFFFF',
                'border': 1,
                'font_size': 11
            })
            
            cell_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1,
                'font_size': 10
            })
            
            date_format = workbook.add_format({
                'num_format': 'yyyy-mm-dd hh:mm',
                'text_wrap': True,
                'valign': 'top',
                'border': 1,
                'font_size': 10
            })
            
            priority_formats = {
                'URGENT': workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1,
                    'bg_color': '#FFE6E6',
                    'font_size': 10
                }),
                'HIGH': workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1,
                    'bg_color': '#FFF2CC',
                    'font_size': 10
                }),
                'MEDIUM': workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1,
                    'bg_color': '#E6F3E6',
                    'font_size': 10
                }),
                'LOW': workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1,
                    'bg_color': '#E6F7FF',
                    'font_size': 10
                }),
                'TURTLE': workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1,
                    'bg_color': '#F0E6FF',
                    'font_size': 10
                })
            }
            
            return header_format, cell_format, date_format, priority_formats
        
        # 워크시트 스타일 적용 함수
        def apply_worksheet_style(worksheet, df, header_format, cell_format, date_format, priority_formats):
            # 열 너비 설정
            worksheet.set_column('A:A', 12)  # 작성자
            worksheet.set_column('B:B', 10)  # 완료여부
            worksheet.set_column('C:C', 12)  # 날짜
            worksheet.set_column('D:D', 18)  # 마감시간
            worksheet.set_column('E:E', 15)  # 프로젝트
            worksheet.set_column('F:F', 25)  # 제목
            worksheet.set_column('G:G', 35)  # 내용
            worksheet.set_column('H:H', 35)  # 메모
            worksheet.set_column('I:I', 12)  # 우선순위
            worksheet.set_column('J:J', 10)  # 개인일정
            
            # 헤더 스타일 적용
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # 데이터 스타일 적용
            for row_num in range(len(df)):
                priority = df.iloc[row_num]['우선순위']
                row_format = priority_formats.get(priority, cell_format)
                
                for col_num, column in enumerate(df.columns):
                    value = df.iloc[row_num][column]
                    if isinstance(value, datetime):
                        worksheet.write(row_num + 1, col_num, value, date_format)
                    else:
                        worksheet.write(row_num + 1, col_num, value, row_format)
        
        # 기본 데이터 수집
        all_data = []
        user_dict = {user.id: user.name for user in users}
        
        for user in users:
            schedules = create_base_query(user.id).all()
            for schedule in schedules:
                all_data.append(schedule_to_dict(schedule, user.name))
        
        if not all_data:
            # 데이터가 없는 경우 빈 엑셀 파일 생성
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                empty_df = pd.DataFrame({'메시지': ['조건에 맞는 일정이 없습니다.']})
                empty_df.to_excel(writer, sheet_name="결과 없음", index=False)
            
            output.seek(0)
            filename = f'schedules_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
            return StreamingResponse(
                output,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        
        # 선택된 출력 옵션이 있는지 확인
        has_custom_options = any([export_by_project, export_by_author, export_by_month, export_by_week, export_by_priority])
        
        if not has_custom_options:
            # 기본 단일 파일 출력
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                header_format, cell_format, date_format, priority_formats = create_formats(workbook)
                
                df = pd.DataFrame(all_data)
                sheet_name = "전체 일정"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                worksheet = writer.sheets[sheet_name]
                apply_worksheet_style(worksheet, df, header_format, cell_format, date_format, priority_formats)
            
            output.seek(0)
            filename = f'schedules_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
            return StreamingResponse(
                output,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        
        # 다중 파일 생성이 필요한 경우
        with tempfile.TemporaryDirectory() as temp_dir:
            files_to_zip = []
            
            # 프로젝트별 파일 생성
            if export_by_project:
                project_data = defaultdict(list)
                for item in all_data:
                    project_name = item['프로젝트'] or '프로젝트 미지정'
                    project_data[project_name].append(item)
                
                for project_name, data in project_data.items():
                    if data:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            workbook = writer.book
                            header_format, cell_format, date_format, priority_formats = create_formats(workbook)
                            
                            df = pd.DataFrame(data)
                            df.to_excel(writer, sheet_name="프로젝트별 일정", index=False)
                            
                            worksheet = writer.sheets["프로젝트별 일정"]
                            apply_worksheet_style(worksheet, df, header_format, cell_format, date_format, priority_formats)
                        
                        filename = f'프로젝트별_{project_name}_{datetime.now().strftime("%Y%m%d")}.xlsx'
                        filepath = os.path.join(temp_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(output.getvalue())
                        files_to_zip.append(filepath)
            
            # 작성자별 파일 생성
            if export_by_author:
                author_data = defaultdict(list)
                for item in all_data:
                    author_data[item['작성자']].append(item)
                
                for author_name, data in author_data.items():
                    if data:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            workbook = writer.book
                            header_format, cell_format, date_format, priority_formats = create_formats(workbook)
                            
                            df = pd.DataFrame(data)
                            df.to_excel(writer, sheet_name="작성자별 일정", index=False)
                            
                            worksheet = writer.sheets["작성자별 일정"]
                            apply_worksheet_style(worksheet, df, header_format, cell_format, date_format, priority_formats)
                        
                        filename = f'작성자별_{author_name}_{datetime.now().strftime("%Y%m%d")}.xlsx'
                        filepath = os.path.join(temp_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(output.getvalue())
                        files_to_zip.append(filepath)
            
            # 월별 파일 생성
            if export_by_month:
                month_data = defaultdict(list)
                for item in all_data:
                    if item['날짜']:
                        month_key = item['날짜'].strftime('%Y년 %m월')
                        month_data[month_key].append(item)
                
                for month_name, data in month_data.items():
                    if data:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            workbook = writer.book
                            header_format, cell_format, date_format, priority_formats = create_formats(workbook)
                            
                            df = pd.DataFrame(data)
                            df.to_excel(writer, sheet_name="월별 일정", index=False)
                            
                            worksheet = writer.sheets["월별 일정"]
                            apply_worksheet_style(worksheet, df, header_format, cell_format, date_format, priority_formats)
                        
                        filename = f'월별_{month_name}_{datetime.now().strftime("%Y%m%d")}.xlsx'
                        filepath = os.path.join(temp_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(output.getvalue())
                        files_to_zip.append(filepath)
            
            # 주별 파일 생성
            if export_by_week:
                week_data = defaultdict(list)
                for item in all_data:
                    if item['날짜']:
                        year, week_num, _ = item['날짜'].isocalendar()
                        week_key = f'{year}년 {week_num}주차'
                        week_data[week_key].append(item)
                
                for week_name, data in week_data.items():
                    if data:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            workbook = writer.book
                            header_format, cell_format, date_format, priority_formats = create_formats(workbook)
                            
                            df = pd.DataFrame(data)
                            df.to_excel(writer, sheet_name="주별 일정", index=False)
                            
                            worksheet = writer.sheets["주별 일정"]
                            apply_worksheet_style(worksheet, df, header_format, cell_format, date_format, priority_formats)
                        
                        filename = f'주별_{week_name}_{datetime.now().strftime("%Y%m%d")}.xlsx'
                        filepath = os.path.join(temp_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(output.getvalue())
                        files_to_zip.append(filepath)
            
            # 우선순위별 파일 생성
            if export_by_priority:
                priority_data = defaultdict(list)
                for item in all_data:
                    priority = item['우선순위'] or '우선순위 미지정'
                    priority_data[priority].append(item)
                
                for priority_name, data in priority_data.items():
                    if data:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            workbook = writer.book
                            header_format, cell_format, date_format, priority_formats = create_formats(workbook)
                            
                            df = pd.DataFrame(data)
                            df.to_excel(writer, sheet_name="우선순위별 일정", index=False)
                            
                            worksheet = writer.sheets["우선순위별 일정"]
                            apply_worksheet_style(worksheet, df, header_format, cell_format, date_format, priority_formats)
                        
                        filename = f'우선순위별_{priority_name}_{datetime.now().strftime("%Y%m%d")}.xlsx'
                        filepath = os.path.join(temp_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(output.getvalue())
                        files_to_zip.append(filepath)
            
            # ZIP 파일 생성
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in files_to_zip:
                    zip_file.write(file_path, os.path.basename(file_path))
            
            zip_buffer.seek(0)
            zip_filename = f'schedules_export_multiple_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
            
            return StreamingResponse(
                zip_buffer,
                media_type='application/zip',
                headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'}
            )
        
    except Exception as e:
        logger.error(f"[EXCEL EXPORT ERROR] {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"엑셀 파일 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/{schedule_id}/collaborators")
def get_schedule_collaborators(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """일정의 공동 작업자 목록을 반환합니다."""
    try:
        # 권한 관리 모듈 사용
        from app.core.permissions import get_schedule_collaborators as get_collaborators
        
        # 일정이 존재하는지 확인
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="일정을 찾을 수 없습니다"
            )
        
        # 일정 소유자이거나 공유된 사용자인지 확인
        if schedule.owner_id != current_user.id:
            shared_schedule = db.query(ScheduleShare).filter(
                ScheduleShare.schedule_id == schedule_id,
                ScheduleShare.shared_with_id == current_user.id
            ).first()
            if not shared_schedule:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="이 일정에 접근할 권한이 없습니다"
                )
        
        # 권한 관리 모듈을 통해 공동 작업자 목록 조회
        collaborators = get_collaborators(db, schedule_id)
        
        return collaborators
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule collaborators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"공동 작업자 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/{schedule_id}/collaborators")
def add_collaborator(
    schedule_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """일정에 공동 작업자를 추가합니다."""
    try:
        # 권한 확인: 일정 소유자이거나 공유 권한이 있는 공동 작업자인지 확인
        from app.core.permissions import can_share_schedule, add_collaborator_to_schedule
        
        if not can_share_schedule(db, current_user.id, schedule_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 일정에 공동 작업자를 추가할 권한이 없습니다"
            )
        
        # 사용자가 존재하는지 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 자신을 공동 작업자로 추가할 수 없음
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자신을 공동 작업자로 추가할 수 없습니다"
            )
        
        # 공동 작업자 추가
        success = add_collaborator_to_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=user_id,
            added_by=current_user.id
        )
        
        if success:
            return {"message": f"사용자 {user.name}을(를) 공동 작업자로 추가했습니다"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="공동 작업자 추가에 실패했습니다"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding collaborator: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"공동 작업자 추가 중 오류가 발생했습니다: {str(e)}"
        )

@router.delete("/{schedule_id}/collaborators/{user_id}")
def remove_collaborator(
    schedule_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """일정에서 공동 작업자를 제거합니다."""
    try:
        # 권한 확인: 일정 소유자이거나 공유 권한이 있는 공동 작업자인지 확인
        from app.core.permissions import can_share_schedule, remove_collaborator_from_schedule
        
        if not can_share_schedule(db, current_user.id, schedule_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 일정에서 공동 작업자를 제거할 권한이 없습니다"
            )
        
        # 공동 작업자 제거
        success = remove_collaborator_from_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=user_id
        )
        
        if success:
            return {"message": "공동 작업자가 제거되었습니다"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="공동 작업자를 찾을 수 없습니다"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing collaborator: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"공동 작업자 제거 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/{schedule_id}/permissions")
def get_schedule_permissions(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """현재 사용자의 특정 일정에 대한 권한 정보를 반환합니다."""
    try:
        from app.core.permissions import get_user_schedule_permissions
        
        # 일정이 존재하는지 확인
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="일정을 찾을 수 없습니다"
            )
        
        # 권한 정보 조회
        permissions = get_user_schedule_permissions(db, current_user.id, schedule_id)
        
        if not permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 일정에 접근할 권한이 없습니다"
            )
        
        return permissions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"권한 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/test-logging")
def test_logging():
    """로깅 시스템 테스트용 엔드포인트"""
    print("🧪 [TEST] 로깅 테스트 엔드포인트 호출됨!")
    logger.info("🧪 [TEST] Logger를 통한 로그 테스트")
    logger.warning("🧪 [TEST] Logger를 통한 경고 테스트")
    logger.error("🧪 [TEST] Logger를 통한 오류 테스트")
    
    return {
        "message": "로깅 테스트 완료",
        "timestamp": datetime.now().isoformat(),
        "test_data": {
            "string": "테스트 문자열",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"key": "value"}
        }
    }
