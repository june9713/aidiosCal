"""
공동 작업자 권한 관리 모듈

이 모듈은 일정에 대한 사용자의 권한을 확인하고 관리하는 함수들을 제공합니다.
"""

from sqlalchemy.orm import Session
from app.models.models import User, Schedule, ScheduleShare
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

def can_edit_schedule(db: Session, user_id: int, schedule_id: int) -> bool:
    """
    사용자가 특정 일정을 수정할 수 있는지 확인
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        schedule_id: 일정 ID
    
    Returns:
        bool: 수정 권한 여부
    """
    try:
        # 일정 소유자인지 확인
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"Schedule {schedule_id} not found")
            return False
        
        if schedule.owner_id == user_id:
            logger.info(f"User {user_id} is owner of schedule {schedule_id}")
            return True
        
        # 공동 작업자인지 확인
        share = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id,
            ScheduleShare.shared_with_id == user_id
        ).first()
        
        if share and hasattr(share, 'can_edit') and share.can_edit:
            logger.info(f"User {user_id} has edit permission for schedule {schedule_id}")
            return True
        
        logger.info(f"User {user_id} has no edit permission for schedule {schedule_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking edit permission: {e}")
        return False

def can_delete_schedule(db: Session, user_id: int, schedule_id: int) -> bool:
    """
    사용자가 특정 일정을 삭제할 수 있는지 확인
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        schedule_id: 일정 ID
    
    Returns:
        bool: 삭제 권한 여부
    """
    try:
        # 일정 소유자인지 확인
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"Schedule {schedule_id} not found")
            return False
        
        if schedule.owner_id == user_id:
            logger.info(f"User {user_id} is owner of schedule {schedule_id}")
            return True
        
        # 공동 작업자인지 확인
        share = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id,
            ScheduleShare.shared_with_id == user_id
        ).first()
        
        if share and hasattr(share, 'can_delete') and share.can_delete:
            logger.info(f"User {user_id} has delete permission for schedule {schedule_id}")
            return True
        
        logger.info(f"User {user_id} has no delete permission for schedule {schedule_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking delete permission: {e}")
        return False

def can_complete_schedule(db: Session, user_id: int, schedule_id: int) -> bool:
    """
    사용자가 특정 일정을 완료 처리할 수 있는지 확인
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        schedule_id: 일정 ID
    
    Returns:
        bool: 완료 처리 권한 여부
    """
    try:
        # 일정 소유자인지 확인
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"Schedule {schedule_id} not found")
            return False
        
        if schedule.owner_id == user_id:
            logger.info(f"User {user_id} is owner of schedule {schedule_id}")
            return True
        
        # 공동 작업자인지 확인
        share = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id,
            ScheduleShare.shared_with_id == user_id
        ).first()
        
        if share and hasattr(share, 'can_complete') and share.can_complete:
            logger.info(f"User {user_id} has complete permission for schedule {schedule_id}")
            return True
        
        logger.info(f"User {user_id} has no complete permission for schedule {schedule_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking complete permission: {e}")
        return False

def can_share_schedule(db: Session, user_id: int, schedule_id: int) -> bool:
    """
    사용자가 특정 일정을 다른 사용자와 공유할 수 있는지 확인
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        schedule_id: 일정 ID
    
    Returns:
        bool: 공유 권한 여부
    """
    try:
        # 일정 소유자인지 확인
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"Schedule {schedule_id} not found")
            return False
        
        if schedule.owner_id == user_id:
            logger.info(f"User {user_id} is owner of schedule {schedule_id}")
            return True
        
        # 공동 작업자인지 확인
        share = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id,
            ScheduleShare.shared_with_id == user_id
        ).first()
        
        if share and hasattr(share, 'can_share') and share.can_share:
            logger.info(f"User {user_id} has share permission for schedule {schedule_id}")
            return True
        
        logger.info(f"User {user_id} has no share permission for schedule {schedule_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking share permission: {e}")
        return False

def get_schedule_collaborators(db: Session, schedule_id: int) -> List[Dict]:
    """
    특정 일정의 공동 작업자 목록을 가져옴
    
    Args:
        db: 데이터베이스 세션
        schedule_id: 일정 ID
    
    Returns:
        List[Dict]: 공동 작업자 정보 리스트
    """
    try:
        collaborators = []
        
        # ScheduleShare 테이블에서 공동 작업자 정보 조회
        shares = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id
        ).all()
        
        for share in shares:
            user = db.query(User).filter(User.id == share.shared_with_id).first()
            if user:
                collaborator_info = {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "role": getattr(share, 'role', 'collaborator'),
                    "can_edit": getattr(share, 'can_edit', True),
                    "can_delete": getattr(share, 'can_delete', True),
                    "can_complete": getattr(share, 'can_complete', True),
                    "can_share": getattr(share, 'can_share', True),
                    "added_at": getattr(share, 'added_at', None)
                }
                collaborators.append(collaborator_info)
        
        logger.info(f"Found {len(collaborators)} collaborators for schedule {schedule_id}")
        return collaborators
        
    except Exception as e:
        logger.error(f"Error getting schedule collaborators: {e}")
        return []

def add_collaborator_to_schedule(
    db: Session, 
    schedule_id: int, 
    user_id: int, 
    added_by: int,
    permissions: Optional[Dict] = None
) -> bool:
    """
    일정에 공동 작업자 추가
    
    Args:
        db: 데이터베이스 세션
        schedule_id: 일정 ID
        user_id: 추가할 사용자 ID
        added_by: 추가한 사용자 ID
        permissions: 권한 설정 (기본값: 모든 권한 허용)
    
    Returns:
        bool: 추가 성공 여부
    """
    try:
        # 기본 권한 설정
        if permissions is None:
            permissions = {
                "can_edit": True,
                "can_delete": True,
                "can_complete": True,
                "can_share": True,
                "role": "collaborator"
            }
        
        # 이미 공동 작업자인지 확인
        existing_share = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id,
            ScheduleShare.shared_with_id == user_id
        ).first()
        
        if existing_share:
            # 기존 권한 업데이트
            for key, value in permissions.items():
                if hasattr(existing_share, key):
                    setattr(existing_share, key, value)
            logger.info(f"Updated existing collaborator {user_id} for schedule {schedule_id}")
        else:
            # 새로운 공동 작업자 추가
            new_share = ScheduleShare(
                schedule_id=schedule_id,
                shared_with_id=user_id,
                **permissions
            )
            db.add(new_share)
            logger.info(f"Added new collaborator {user_id} to schedule {schedule_id}")
        
        db.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error adding collaborator: {e}")
        db.rollback()
        return False

def remove_collaborator_from_schedule(db: Session, schedule_id: int, user_id: int) -> bool:
    """
    일정에서 공동 작업자 제거
    
    Args:
        db: 데이터베이스 세션
        schedule_id: 일정 ID
        user_id: 제거할 사용자 ID
    
    Returns:
        bool: 제거 성공 여부
    """
    try:
        share = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id,
            ScheduleShare.shared_with_id == user_id
        ).first()
        
        if share:
            db.delete(share)
            db.commit()
            logger.info(f"Removed collaborator {user_id} from schedule {schedule_id}")
            return True
        else:
            logger.warning(f"Collaborator {user_id} not found for schedule {schedule_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error removing collaborator: {e}")
        db.rollback()
        return False

def get_user_schedule_permissions(db: Session, user_id: int, schedule_id: int) -> Dict:
    """
    사용자의 특정 일정에 대한 권한 정보를 가져옴
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        schedule_id: 일정 ID
    
    Returns:
        Dict: 권한 정보
    """
    try:
        # 일정 소유자인지 확인
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return {}
        
        if schedule.owner_id == user_id:
            return {
                "is_owner": True,
                "can_edit": True,
                "can_delete": True,
                "can_complete": True,
                "can_share": True,
                "role": "owner"
            }
        
        # 공동 작업자인지 확인
        share = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id,
            ScheduleShare.shared_with_id == user_id
        ).first()
        
        if share:
            return {
                "is_owner": False,
                "can_edit": getattr(share, 'can_edit', True),
                "can_delete": getattr(share, 'can_delete', True),
                "can_complete": getattr(share, 'can_complete', True),
                "can_share": getattr(share, 'can_share', True),
                "role": getattr(share, 'role', 'collaborator')
            }
        
        return {
            "is_owner": False,
            "can_edit": False,
            "can_delete": False,
            "can_complete": False,
            "can_share": False,
            "role": "none"
        }
        
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        return {}
