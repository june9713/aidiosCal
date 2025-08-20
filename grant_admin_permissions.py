#!/usr/bin/env python3
"""
june9713과 pci8099 사용자에게 모든 스케줄에 대한 관리자 권한을 부여하는 스크립트

이 스크립트는 다음을 수행합니다:
1. june9713과 pci8099 사용자 ID를 찾습니다
2. 모든 스케줄에 대해 이 두 사용자를 공동 작업자로 추가합니다
3. 모든 권한(수정, 삭제, 완료, 공유)을 부여합니다
"""

import sqlite3
import os
from datetime import datetime

def get_db_path():
    """데이터베이스 파일 경로 반환"""
    return "sql_app.db"

def check_database_exists():
    """데이터베이스 파일 존재 여부 확인"""
    db_path = get_db_path()
    return os.path.exists(db_path)

def grant_admin_permissions():
    """june9713과 pci8099 사용자에게 모든 스케줄에 대한 관리자 권한 부여"""
    
    if not check_database_exists():
        print("❌ 데이터베이스 파일을 찾을 수 없습니다: sql_app.db")
        return False
    
    db_path = get_db_path()
    print(f"📂 데이터베이스 경로: {db_path}")
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 june9713과 pci8099 사용자 ID 확인 중...")
        
        # 사용자 ID 조회
        cursor.execute("SELECT id, username, name FROM users WHERE username IN ('june9713', 'pci8099')")
        target_users = cursor.fetchall()
        
        if not target_users:
            print("❌ june9713 또는 pci8099 사용자를 찾을 수 없습니다.")
            return False
        
        print(f"✅ 대상 사용자 {len(target_users)}명 발견:")
        for user_id, username, name in target_users:
            print(f"   - ID: {user_id}, 사용자명: {username}, 이름: {name}")
        
        # 모든 스케줄 조회
        print("\n📅 모든 스케줄 조회 중...")
        cursor.execute("SELECT id, title, owner_id FROM schedules WHERE is_deleted = 0")
        all_schedules = cursor.fetchall()
        
        if not all_schedules:
            print("❌ 스케줄이 없습니다.")
            return False
        
        print(f"✅ 총 {len(all_schedules)}개의 스케줄 발견")
        
        # schedule_shares 테이블 존재 여부 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schedule_shares'")
        if not cursor.fetchone():
            print("❌ schedule_shares 테이블이 존재하지 않습니다.")
            return False
        
        # 각 스케줄에 대해 권한 부여
        print("\n🔧 각 스케줄에 관리자 권한 부여 중...")
        
        for schedule_id, title, owner_id in all_schedules:
            print(f"\n📋 스케줄 ID: {schedule_id}, 제목: {title}")
            
            for user_id, username, name in target_users:
                # 이미 공동 작업자인지 확인
                cursor.execute("""
                    SELECT id FROM schedule_shares 
                    WHERE schedule_id = ? AND shared_with_id = ?
                """, (schedule_id, user_id))
                
                existing_share = cursor.fetchone()
                
                if existing_share:
                    # 기존 권한 업데이트
                    cursor.execute("""
                        UPDATE schedule_shares 
                        SET can_edit = 1, can_delete = 1, can_complete = 1, can_share = 1,
                            role = 'admin', created_at = ?
                        WHERE schedule_id = ? AND shared_with_id = ?
                    """, (datetime.now(), schedule_id, user_id))
                    print(f"   ✅ {username}: 기존 권한을 관리자 권한으로 업데이트")
                else:
                    # 새로운 공동 작업자 추가
                    cursor.execute("""
                        INSERT INTO schedule_shares 
                        (schedule_id, shared_with_id, can_edit, can_delete, can_complete, can_share, role, added_at)
                        VALUES (?, ?, 1, 1, 1, 1, 'admin', ?)
                    """, (schedule_id, user_id, datetime.now()))
                    print(f"   ➕ {username}: 새로운 관리자로 추가")
        
        # 변경사항 커밋
        conn.commit()
        print(f"\n✅ 모든 변경사항이 성공적으로 저장되었습니다!")
        
        # 결과 확인
        print("\n🔍 권한 부여 결과 확인...")
        for user_id, username, name in target_users:
            cursor.execute("""
                SELECT COUNT(*) FROM schedule_shares 
                WHERE shared_with_id = ? AND role = 'admin'
            """, (user_id,))
            admin_schedules_count = cursor.fetchone()[0]
            print(f"   - {username}: {admin_schedules_count}개 스케줄에 관리자 권한 보유")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    """메인 함수"""
    print("🚀 june9713과 pci8099 사용자에게 관리자 권한 부여 시작")
    print("=" * 60)
    
    success = grant_admin_permissions()
    
    if success:
        print("\n🎉 모든 작업이 성공적으로 완료되었습니다!")
        print("\n📋 부여된 권한:")
        print("   - 모든 스케줄 수정 권한")
        print("   - 모든 스케줄 삭제 권한") 
        print("   - 모든 스케줄 완료 처리 권한")
        print("   - 모든 스케줄 공유 권한")
        print("   - 역할: admin")
    else:
        print("\n❌ 작업 중 오류가 발생했습니다.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
