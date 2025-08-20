"""
공동 작업자 권한 관리 모듈

이 모듈은 일정에 대한 사용자의 권한을 확인하고 관리하는 함수들을 제공합니다.
"""

from sqlalchemy.orm import Session, joinedload
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
        # 사용자의 역할 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            return False
        
        # admin 사용자는 모든 일정에 대한 권한을 가짐
        if user.role == "admin":
            logger.info(f"User {user_id} is admin, has edit permission for all schedules")
            return True
        
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
        # 사용자의 역할 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            return False
        
        # admin 사용자는 모든 일정에 대한 권한을 가짐
        if user.role == "admin":
            logger.info(f"User {user_id} is admin, has delete permission for all schedules")
            return True
        
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
        # 사용자의 역할 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            return False
        
        # admin 사용자는 모든 일정에 대한 권한을 가짐
        if user.role == "admin":
            logger.info(f"User {user_id} is admin, has complete permission for all schedules")
            return True
        
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
        # 사용자의 역할 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            return False
        
        # admin 사용자는 모든 일정에 대한 권한을 가짐
        if user.role == "admin":
            logger.info(f"User {user_id} is admin, has share permission for all schedules")
            return True
        
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
    특정 일정의 공동 작업자 목록을 반환
    
    Args:
        db: 데이터베이스 세션
        schedule_id: 일정 ID
    
    Returns:
        List[Dict]: 공동 작업자 정보 리스트
    """
    try:
        shares = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule_id
        ).options(
            joinedload(ScheduleShare.shared_with)
        ).all()
        
        collaborators = []
        for share in shares:
            collaborator_info = {
                "user_id": share.shared_with_id,
                "username": share.shared_with.username,
                "name": share.shared_with.name,
                "can_edit": getattr(share, 'can_edit', True),
                "can_delete": getattr(share, 'can_delete', True),
                "can_complete": getattr(share, 'can_complete', True),
                "can_share": getattr(share, 'can_share', True),
                "role": getattr(share, 'role', 'collaborator'),
                "added_at": share.added_at
            }
            collaborators.append(collaborator_info)
        
        logger.info(f"Found {len(collaborators)} collaborators for schedule {schedule_id}")
        return collaborators
    except Exception as e:
        logger.error(f"Error getting schedule collaborators: {e}")
        return []

def check_if_users_are_collaborators(db: Session, current_user_id: int, user_ids: List[int]) -> bool:
    """
    선택된 사용자들이 현재 사용자와 공동작업자 관계인지 확인
    
    Args:
        db: 데이터베이스 세션
        current_user_id: 현재 사용자 ID
        user_ids: 확인할 사용자 ID 리스트
    
    Returns:
        bool: 모든 선택된 사용자가 공동작업자인 경우 True
    """
    try:
        if not user_ids:
            return False
            
        # 현재 사용자가 소유한 일정 중에서 선택된 사용자들과 공유된 일정이 있는지 확인
        shared_schedules = db.query(ScheduleShare).join(Schedule).filter(
            Schedule.owner_id == current_user_id,
            ScheduleShare.shared_with_id.in_(user_ids)
        ).first()
        
        if shared_schedules:
            logger.info(f"Users {user_ids} are collaborators of current user {current_user_id}")
            return True
            
        # 현재 사용자가 다른 사용자의 일정에 공동작업자로 포함된 경우도 확인
        for user_id in user_ids:
            user_schedules = db.query(ScheduleShare).filter(
                ScheduleShare.schedule_id == Schedule.id,
                Schedule.owner_id == user_id,
                ScheduleShare.shared_with_id == current_user_id
            ).first()
            
            if user_schedules:
                logger.info(f"Current user {current_user_id} is collaborator of user {user_id}")
                return True
        
        logger.info(f"Users {user_ids} are not collaborators of current user {current_user_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking if users are collaborators: {e}")
        return False

def get_accessible_users_for_collaborators(db: Session, current_user_id: int, collaborator_user_ids: List[int]) -> List[int]:
    """
    공동작업자가 선택된 경우, 접근 가능한 사용자들의 ID 리스트를 반환
    
    Args:
        db: 데이터베이스 세션
        current_user_id: 현재 사용자 ID
        collaborator_user_ids: 공동작업자 사용자 ID 리스트
    
    Returns:
        List[int]: 접근 가능한 사용자 ID 리스트
    """
    try:
        accessible_users = set()
        accessible_users.add(current_user_id)  # 자신은 항상 접근 가능
        
        # 선택된 공동작업자들 추가
        accessible_users.update(collaborator_user_ids)
        
        # 현재 사용자가 소유한 일정에 포함된 다른 공동작업자들 찾기
        current_user_collaborators = db.query(ScheduleShare.shared_with_id).filter(
            ScheduleShare.schedule_id == Schedule.id,
            Schedule.owner_id == current_user_id
        ).distinct().all()
        
        for collaborator in current_user_collaborators:
            accessible_users.add(collaborator[0])
        
        # 선택된 공동작업자들이 소유한 일정에 포함된 다른 사용자들 찾기
        for collaborator_id in collaborator_user_ids:
            collaborator_schedules = db.query(ScheduleShare.shared_with_id).filter(
                ScheduleShare.schedule_id == Schedule.id,
                Schedule.owner_id == collaborator_id
            ).distinct().all()
            
            for shared_user in collaborator_schedules:
                accessible_users.add(shared_user[0])
        
        result = list(accessible_users)
        logger.info(f"Accessible users for collaborators {collaborator_user_ids}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting accessible users for collaborators: {e}")
        return [current_user_id]  # 오류 발생 시 최소한 자신만 접근 가능

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
        # 사용자의 역할 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}
        
        # admin 사용자는 모든 일정에 대한 모든 권한을 가짐
        if user.role == "admin":
            return {
                "is_owner": False,
                "can_edit": True,
                "can_delete": True,
                "can_complete": True,
                "can_share": True,
                "role": "admin"
            }
        
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
