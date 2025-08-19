from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Alarm, Schedule
from app.schemas.schemas import Alarm as AlarmSchema, AlarmCreate
from app.routers.auth import get_current_active_user
from app.models.models import User

router = APIRouter()

@router.get("/", response_model=List[AlarmSchema])
def get_alarms(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """사용자의 알림 목록을 반환합니다."""
    alarms = db.query(Alarm).filter(
        Alarm.user_id == current_user.id,
        Alarm.is_deleted == False
    ).order_by(
        Alarm.created_at.desc()
    ).offset(skip).limit(limit).all()
    return alarms

@router.post("/ack_alarms/{alarm_id}/ack")
def acknowledge_alarm(
    alarm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """알림을 확인 처리합니다."""
    alarm = db.query(Alarm).filter(
        Alarm.id == alarm_id,
        Alarm.user_id == current_user.id
    ).first()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    alarm.is_acked = True
    alarm.acked_at = datetime.now()
    db.commit()
    return {"message": "Alarm acknowledged", "alarm_id": alarm_id}

@router.delete("/delete_alarms/{alarm_id}")
def delete_alarm(
    alarm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """개별 알림을 삭제합니다 (soft delete)."""
    alarm = db.query(Alarm).filter(
        Alarm.id == alarm_id,
        Alarm.user_id == current_user.id,
        Alarm.is_deleted == False
    ).first()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    # 실제 삭제 대신 is_deleted 플래그를 True로 설정
    
    alarm.is_deleted = True
    alarm.is_acked = True
    
    db.commit()
    return {"message": "Alarm deleted", "alarm_id": alarm_id}

@router.delete("/clear_alarms/clear")
def clear_all_alarms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """모든 알림을 삭제합니다 (soft delete)."""
    db.query(Alarm).filter(
        Alarm.user_id == current_user.id,
        Alarm.is_deleted == False
    ).update({"is_deleted": True})
    db.commit()
    return {"message": "All alarms cleared"}

async def confirm_clear_alarms():
    """알림 전체 삭제 전 2단계 확인"""
    # 프론트엔드에서 2단계 확인을 처리하므로 여기서는 True를 반환
    return True

def create_alarm(
    db: Session,
    user_id: int,
    alarm_type: str,
    message: str,
    schedule_id: int
):
    """새로운 알림을 생성합니다."""
    alarm = Alarm(
        user_id=user_id,
        type=alarm_type,
        message=message,
        schedule_id=schedule_id
    )
    db.add(alarm)
    db.commit()
    db.refresh(alarm)
    return alarm 