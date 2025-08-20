#!/usr/bin/env python3
"""
권한 관리 시스템 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import get_db
from app.core.permissions import (
    can_edit_schedule,
    can_delete_schedule,
    can_complete_schedule,
    can_share_schedule,
    add_collaborator_to_schedule,
    get_user_schedule_permissions
)
from app.models.models import User, Schedule, ScheduleShare
from app.core.database import Base

def test_permissions():
    """권한 관리 시스템 테스트"""
    print("🔐 권한 관리 시스템 테스트 시작")
    
    # 데이터베이스 연결
    engine = create_engine("sqlite:///sql_app.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 1. 사용자 정보 조회
        print("\n1️⃣ 사용자 정보 조회")
        users = db.query(User).limit(3).all()
        for user in users:
            print(f"   사용자 ID: {user.id}, 이름: {user.name}, 사용자명: {user.username}")
        
        if len(users) < 2:
            print("❌ 테스트를 위한 사용자가 부족합니다.")
            return
        
        owner_user = users[0]  # 일정 소유자
        collaborator_user = users[1]  # 공동 작업자
        
        # 2. 일정 정보 조회
        print("\n2️⃣ 일정 정보 조회")
        schedule = db.query(Schedule).filter(Schedule.owner_id == owner_user.id).first()
        if not schedule:
            print("❌ 테스트할 일정이 없습니다.")
            return
        
        print(f"   일정 ID: {schedule.id}, 제목: {schedule.title}, 소유자: {schedule.owner_id}")
        
        # 3. 권한 확인 (소유자)
        print("\n3️⃣ 소유자 권한 확인")
        owner_permissions = get_user_schedule_permissions(db, owner_user.id, schedule.id)
        print(f"   소유자 권한: {owner_permissions}")
        
        # 4. 권한 확인 (공동 작업자 - 아직 추가되지 않음)
        print("\n4️⃣ 공동 작업자 권한 확인 (추가 전)")
        collaborator_permissions = get_user_schedule_permissions(db, collaborator_user.id, schedule.id)
        print(f"   공동 작업자 권한: {collaborator_permissions}")
        
        # 5. 공동 작업자 추가
        print("\n5️⃣ 공동 작업자 추가")
        success = add_collaborator_to_schedule(
            db, 
            schedule.id, 
            collaborator_user.id, 
            owner_user.id,
            {
                "can_edit": True,
                "can_delete": False,
                "can_complete": True,
                "can_share": False,
                "role": "editor"
            }
        )
        
        if success:
            print("   ✅ 공동 작업자 추가 성공")
        else:
            print("   ❌ 공동 작업자 추가 실패")
            return
        
        # 6. 권한 확인 (공동 작업자 - 추가 후)
        print("\n6️⃣ 공동 작업자 권한 확인 (추가 후)")
        collaborator_permissions = get_user_schedule_permissions(db, collaborator_user.id, schedule.id)
        print(f"   공동 작업자 권한: {collaborator_permissions}")
        
        # 7. 개별 권한 함수 테스트
        print("\n7️⃣ 개별 권한 함수 테스트")
        print(f"   수정 권한: {can_edit_schedule(db, collaborator_user.id, schedule.id)}")
        print(f"   삭제 권한: {can_delete_schedule(db, collaborator_user.id, schedule.id)}")
        print(f"   완료 권한: {can_complete_schedule(db, collaborator_user.id, schedule.id)}")
        print(f"   공유 권한: {can_share_schedule(db, collaborator_user.id, schedule.id)}")
        
        # 8. 데이터베이스 상태 확인
        print("\n8️⃣ 데이터베이스 상태 확인")
        share_record = db.query(ScheduleShare).filter(
            ScheduleShare.schedule_id == schedule.id,
            ScheduleShare.shared_with_id == collaborator_user.id
        ).first()
        
        if share_record:
            print(f"   공유 레코드 ID: {share_record.id}")
            print(f"   can_edit: {getattr(share_record, 'can_edit', 'N/A')}")
            print(f"   can_delete: {getattr(share_record, 'can_delete', 'N/A')}")
            print(f"   can_complete: {getattr(share_record, 'can_complete', 'N/A')}")
            print(f"   can_share: {getattr(share_record, 'can_share', 'N/A')}")
            print(f"   role: {getattr(share_record, 'role', 'N/A')}")
        else:
            print("   ❌ 공유 레코드를 찾을 수 없습니다.")
        
        print("\n✅ 권한 관리 시스템 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_permissions()
