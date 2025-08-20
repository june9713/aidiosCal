#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB에 공동작업자가 추가된 일정이 있는지 확인하는 스크립트
"""

import sys
import os
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from app.models.models import Schedule, ScheduleShare, User

def check_collaborators():
    """DB에 공동작업자가 추가된 일정이 있는지 확인"""
    
    # 데이터베이스 연결
    SQLALCHEMY_DATABASE_URL = "sqlite:///sql_app.db"
    
    try:
        print("데이터베이스에 연결 중...")
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
        
        # 세션 생성
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("연결 성공!")
        print("=" * 60)
        
        # 1. 공유된 일정이 있는지 확인
        print("1. 공유된 일정 확인:")
        shared_schedules = db.query(ScheduleShare).all()
        
        if not shared_schedules:
            print("   - 공유된 일정이 없습니다.")
        else:
            print(f"   - 공유된 일정 수: {len(shared_schedules)}")
            print()
            
            for share in shared_schedules:
                schedule = db.query(Schedule).filter(Schedule.id == share.schedule_id).first()
                user = db.query(User).filter(User.id == share.shared_with_id).first()
                owner = db.query(User).filter(User.id == schedule.owner_id).first()
                
                print(f"   일정 ID: {share.schedule_id}")
                print(f"   일정 제목: {schedule.title if schedule else 'N/A'}")
                print(f"   일정 소유자: {owner.name if owner else 'N/A'} ({owner.username if owner else 'N/A'})")
                print(f"   공유 대상: {user.name if user else 'N/A'} ({user.username if user else 'N/A'})")
                print(f"   공유 역할: {share.role}")
                print(f"   편집 권한: {'예' if share.can_edit else '아니오'}")
                print(f"   삭제 권한: {'예' if share.can_delete else '아니오'}")
                print(f"   완료 권한: {'예' if share.can_complete else '아니오'}")
                print(f"   공유 권한: {'예' if share.can_share else '아니오'}")
                print(f"   공유 메모: {share.memo if share.memo else '없음'}")
                print(f"   공유 일시: {share.created_at}")
                print(f"   추가 일시: {share.added_at}")
                print("   " + "-" * 40)
        
        print()
        
        # 2. 사용자별 공유 현황 요약
        print("2. 사용자별 공유 현황:")
        # 각 사용자별로 공유받은 일정 수를 계산
        user_share_counts = {}
        for share in shared_schedules:
            user_id = share.shared_with_id
            if user_id not in user_share_counts:
                user_share_counts[user_id] = 0
            user_share_counts[user_id] += 1
        
        if not user_share_counts:
            print("   - 공유 대상이 된 사용자가 없습니다.")
        else:
            for user_id, count in user_share_counts.items():
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    print(f"   {user.name} ({user.username}): {count}개 일정 공유됨")
        
        print()
        
        # 3. 일정별 공유자 수
        print("3. 일정별 공유자 수:")
        # 각 일정별로 공유자 수를 계산
        schedule_share_counts = {}
        for share in shared_schedules:
            schedule_id = share.schedule_id
            if schedule_id not in schedule_share_counts:
                schedule_share_counts[schedule_id] = 0
            schedule_share_counts[schedule_id] += 1
        
        if not schedule_share_counts:
            print("   - 공유자가 있는 일정이 없습니다.")
        else:
            for schedule_id, count in schedule_share_counts.items():
                schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
                title = schedule.title if schedule else 'N/A'
                print(f"   일정 ID {schedule_id}: '{title}' - 공유자 {count}명")
        
        print()
        
        # 4. 최근 공유 활동
        print("4. 최근 공유 활동 (최근 10개):")
        recent_shares = db.query(ScheduleShare).order_by(ScheduleShare.created_at.desc()).limit(10).all()
        
        if not recent_shares:
            print("   - 공유 활동이 없습니다.")
        else:
            for share in recent_shares:
                schedule = db.query(Schedule).filter(Schedule.id == share.schedule_id).first()
                user = db.query(User).filter(User.id == share.shared_with_id).first()
                owner = db.query(User).filter(User.id == schedule.owner_id).first()
                
                print(f"   {share.created_at.strftime('%Y-%m-%d %H:%M')} - "
                      f"'{schedule.title if schedule else 'N/A'}' "
                      f"({owner.name if owner else 'N/A'} → {user.name if user else 'N/A'})")
        
        print()
        print("=" * 60)
        print("확인 완료!")
        
        # 요약 정보
        total_shares = len(shared_schedules)
        unique_schedules = len(set([s.schedule_id for s in shared_schedules]))
        unique_users = len(set([s.shared_with_id for s in shared_schedules]))
        
        print(f"\n📊 요약:")
        print(f"   총 공유 건수: {total_shares}")
        print(f"   공유된 일정 수: {unique_schedules}")
        print(f"   공유 대상 사용자 수: {unique_users}")
        
        if total_shares > 0:
            print(f"\n✅ DB에 공동작업자가 추가된 일정이 {unique_schedules}개 있습니다.")
        else:
            print(f"\n❌ DB에 공동작업자가 추가된 일정이 없습니다.")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    check_collaborators()
