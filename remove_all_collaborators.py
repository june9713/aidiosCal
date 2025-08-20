#!/usr/bin/env python3
"""
데이터베이스에서 모든 공유작업자들을 제거하고 작업을 소유자 단독 작업으로 변경하는 스크립트
"""

import sys
import os
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.models import ScheduleShare, Schedule, User
from app.core.database import SQLALCHEMY_DATABASE_URL

def remove_all_collaborators():
    """
    데이터베이스에서 모든 공유작업자들을 제거하고 작업을 소유자 단독 작업으로 변경
    """
    print("=" * 60)
    print("공유작업자 제거 및 소유자 단독 작업 변경 스크립트")
    print("=" * 60)
    
    # 데이터베이스 연결
    try:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print(f"[{datetime.now()}] 데이터베이스 연결 성공")
        
        # 현재 공유작업자 수 확인
        total_shares = db.query(ScheduleShare).count()
        print(f"[{datetime.now()}] 현재 공유작업자 수: {total_shares}개")
        
        if total_shares == 0:
            print(f"[{datetime.now()}] 제거할 공유작업자가 없습니다.")
            return
        
        # 공유작업자 정보 조회 (삭제 전 로그용)
        shares_info = db.query(ScheduleShare).all()
        print(f"\n[{datetime.now()}] 제거할 공유작업자 정보:")
        for share in shares_info:
            schedule = db.query(Schedule).filter(Schedule.id == share.schedule_id).first()
            user = db.query(User).filter(User.id == share.shared_with_id).first()
            owner = db.query(User).filter(User.id == schedule.owner_id).first() if schedule else None
            
            if schedule and user and owner:
                print(f"  - 작업: '{schedule.title}' (ID: {schedule.id})")
                print(f"    소유자: {owner.name} ({owner.username})")
                print(f"    공유작업자: {user.name} ({user.username})")
                print(f"    권한: 편집={share.can_edit}, 삭제={share.can_delete}, 완료={share.can_complete}, 공유={share.can_share}")
                print()
        
        # 사용자 확인
        confirm = input(f"\n총 {total_shares}개의 공유작업자를 제거하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("작업이 취소되었습니다.")
            return
        
        # 공유작업자 삭제
        print(f"\n[{datetime.now()}] 공유작업자 삭제 시작...")
        
        # ScheduleShare 테이블의 모든 레코드 삭제
        deleted_count = db.query(ScheduleShare).delete()
        
        # 변경사항 커밋
        db.commit()
        
        print(f"[{datetime.now()}] 공유작업자 삭제 완료: {deleted_count}개")
        
        # 삭제 후 확인
        remaining_shares = db.query(ScheduleShare).count()
        print(f"[{datetime.now()}] 남은 공유작업자 수: {remaining_shares}개")
        
        if remaining_shares == 0:
            print(f"[{datetime.now()}] 모든 공유작업자가 성공적으로 제거되었습니다.")
        else:
            print(f"[{datetime.now()}] 경고: {remaining_shares}개의 공유작업자가 남아있습니다.")
        
        # 작업별 상태 확인
        total_schedules = db.query(Schedule).count()
        schedules_with_shares = db.query(Schedule).join(ScheduleShare).distinct().count()
        
        print(f"\n[{datetime.now()}] 작업 상태 요약:")
        print(f"  - 전체 작업 수: {total_schedules}개")
        print(f"  - 공유 작업 수: {schedules_with_shares}개")
        print(f"  - 단독 작업 수: {total_schedules - schedules_with_shares}개")
        
        print(f"\n[{datetime.now()}] 작업 완료!")
        
    except Exception as e:
        print(f"[{datetime.now()}] 오류 발생: {str(e)}")
        if 'db' in locals():
            db.rollback()
        raise
    finally:
        if 'db' in locals():
            db.close()

def verify_removal():
    """
    공유작업자 제거 결과를 검증
    """
    print("\n" + "=" * 60)
    print("공유작업자 제거 결과 검증")
    print("=" * 60)
    
    try:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # ScheduleShare 테이블 확인
        shares_count = db.query(ScheduleShare).count()
        print(f"[{datetime.now()}] ScheduleShare 테이블 레코드 수: {shares_count}개")
        
        if shares_count == 0:
            print(f"[{datetime.now()}] ✓ 모든 공유작업자가 성공적으로 제거되었습니다.")
        else:
            print(f"[{datetime.now()}] ✗ {shares_count}개의 공유작업자가 남아있습니다.")
        
        # 공유 작업이 있는지 확인
        schedules_with_shares = db.query(Schedule).join(ScheduleShare).distinct().count()
        print(f"[{datetime.now()}] 공유 작업 수: {schedules_with_shares}개")
        
        if schedules_with_shares == 0:
            print(f"[{datetime.now()}] ✓ 모든 작업이 소유자 단독 작업으로 변경되었습니다.")
        else:
            print(f"[{datetime.now()}] ✗ {schedules_with_shares}개의 작업이 여전히 공유 상태입니다.")
        
        # 데이터베이스 무결성 확인
        print(f"\n[{datetime.now()}] 데이터베이스 무결성 확인 중...")
        
        # 고아 레코드 확인 (ScheduleShare가 참조하는 존재하지 않는 Schedule)
        orphan_shares = db.query(ScheduleShare).outerjoin(Schedule).filter(Schedule.id.is_(None)).count()
        if orphan_shares == 0:
            print(f"[{datetime.now()}] ✓ ScheduleShare 테이블 무결성 확인 완료")
        else:
            print(f"[{datetime.now()}] ⚠ 고아 ScheduleShare 레코드: {orphan_shares}개")
        
        # 고아 레코드 확인 (ScheduleShare가 참조하는 존재하지 않는 User)
        orphan_user_shares = db.query(ScheduleShare).outerjoin(User, ScheduleShare.shared_with_id == User.id).filter(User.id.is_(None)).count()
        if orphan_user_shares == 0:
            print(f"[{datetime.now()}] ✓ User 참조 무결성 확인 완료")
        else:
            print(f"[{datetime.now()}] ⚠ 고아 User 참조: {orphan_user_shares}개")
        
    except Exception as e:
        print(f"[{datetime.now()}] 검증 중 오류 발생: {str(e)}")
        raise
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    try:
        # 공유작업자 제거 실행
        remove_all_collaborators()
        
        # 결과 검증
        verify_removal()
        
        print("\n" + "=" * 60)
        print("스크립트 실행 완료!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 스크립트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n스크립트 실행 중 오류가 발생했습니다: {str(e)}")
        sys.exit(1)
