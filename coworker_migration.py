#!/usr/bin/env python3
"""
공동 작업자 기능을 위한 데이터베이스 마이그레이션 스크립트

이 스크립트는 다음과 같은 작업을 수행합니다:
1. ScheduleShare 테이블에 권한 관련 컬럼 추가
2. 기존 공유 데이터에 기본 권한 설정
3. 공동 작업자 권한 관리 테이블 생성
"""

import sqlite3
import os
import sys
from datetime import datetime
import traceback

def backup_database(db_path):
    """데이터베이스 백업"""
    backup_path = f"{db_path}.backup_coworker_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ 데이터베이스 백업 완료: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ 데이터베이스 백업 실패: {e}")
        return False

def check_table_exists(cursor, table_name):
    """테이블 존재 여부 확인"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def add_coworker_permissions_to_schedule_shares(cursor):
    """ScheduleShare 테이블에 공동 작업자 권한 컬럼 추가"""
    try:
        # 기존 컬럼 확인
        cursor.execute("PRAGMA table_info(schedule_shares)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 필요한 컬럼들 추가
        new_columns = [
            ("can_edit", "BOOLEAN DEFAULT 1"),
            ("can_delete", "BOOLEAN DEFAULT 1"),
            ("can_complete", "BOOLEAN DEFAULT 1"),
            ("can_share", "BOOLEAN DEFAULT 1"),
            ("role", "TEXT DEFAULT 'collaborator'"),
            ("added_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for column_name, column_def in new_columns:
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE schedule_shares ADD COLUMN {column_name} {column_def}")
                print(f"✅ 컬럼 추가: {column_name}")
            else:
                print(f"ℹ️ 컬럼 이미 존재: {column_name}")
        
        return True
    except Exception as e:
        print(f"❌ ScheduleShare 테이블 수정 실패: {e}")
        return False

def create_coworker_permissions_table(cursor):
    """공동 작업자 권한 관리 테이블 생성"""
    try:
        if not check_table_exists(cursor, "coworker_permissions"):
            cursor.execute("""
                CREATE TABLE coworker_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    can_edit BOOLEAN DEFAULT 1,
                    can_delete BOOLEAN DEFAULT 1,
                    can_complete BOOLEAN DEFAULT 1,
                    can_share BOOLEAN DEFAULT 1,
                    role TEXT DEFAULT 'collaborator',
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    added_by INTEGER,
                    FOREIGN KEY (schedule_id) REFERENCES schedules (id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (added_by) REFERENCES users (id) ON DELETE SET NULL,
                    UNIQUE(schedule_id, user_id)
                )
            """)
            print("✅ coworker_permissions 테이블 생성 완료")
        else:
            print("ℹ️ coworker_permissions 테이블 이미 존재")
        
        return True
    except Exception as e:
        print(f"❌ coworker_permissions 테이블 생성 실패: {e}")
        return False

def create_indexes(cursor):
    """성능 향상을 위한 인덱스 생성"""
    try:
        indexes = [
            ("idx_coworker_permissions_schedule", "coworker_permissions", "schedule_id"),
            ("idx_coworker_permissions_user", "coworker_permissions", "user_id"),
            ("idx_schedule_shares_schedule", "schedule_shares", "schedule_id"),
            ("idx_schedule_shares_user", "schedule_shares", "shared_with_id")
        ]
        
        for index_name, table_name, column_name in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})")
                print(f"✅ 인덱스 생성: {index_name}")
            except Exception as e:
                print(f"ℹ️ 인덱스 생성 실패 (이미 존재할 수 있음): {index_name} - {e}")
        
        return True
    except Exception as e:
        print(f"❌ 인덱스 생성 실패: {e}")
        return False

def migrate_existing_data(cursor):
    """기존 공유 데이터를 새로운 권한 시스템으로 마이그레이션"""
    try:
        # 기존 schedule_shares 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM schedule_shares")
        count = cursor.fetchone()[0]
        print(f"ℹ️ 기존 공유 데이터 수: {count}")
        
        if count > 0:
            # 기존 데이터에 기본 권한 설정
            cursor.execute("""
                UPDATE schedule_shares 
                SET can_edit = 1, can_delete = 1, can_complete = 1, can_share = 1,
                    role = 'collaborator', added_at = CURRENT_TIMESTAMP
                WHERE can_edit IS NULL
            """)
            print("✅ 기존 공유 데이터 권한 설정 완료")
        
        return True
    except Exception as e:
        print(f"❌ 기존 데이터 마이그레이션 실패: {e}")
        return False

def verify_migration(cursor):
    """마이그레이션 결과 검증"""
    try:
        # ScheduleShare 테이블 구조 확인
        cursor.execute("PRAGMA table_info(schedule_shares)")
        columns = [column[1] for column in cursor.fetchall()]
        required_columns = ['can_edit', 'can_delete', 'can_complete', 'can_share', 'role', 'added_at']
        
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            print(f"❌ 누락된 컬럼: {missing_columns}")
            return False
        
        # coworker_permissions 테이블 존재 확인
        if not check_table_exists(cursor, "coworker_permissions"):
            print("❌ coworker_permissions 테이블이 생성되지 않음")
            return False
        
        print("✅ 마이그레이션 검증 완료")
        return True
    except Exception as e:
        print(f"❌ 마이그레이션 검증 실패: {e}")
        return False

def main():
    """메인 마이그레이션 함수"""
    db_path = "sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return False
    
    print("🚀 공동 작업자 기능 데이터베이스 마이그레이션 시작")
    print(f"📁 대상 데이터베이스: {db_path}")
    
    # 데이터베이스 백업
    if not backup_database(db_path):
        print("❌ 백업 실패로 마이그레이션을 중단합니다.")
        return False
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📋 마이그레이션 단계별 진행 상황:")
        
        # 1단계: ScheduleShare 테이블에 권한 컬럼 추가
        print("\n1️⃣ ScheduleShare 테이블 권한 컬럼 추가...")
        if not add_coworker_permissions_to_schedule_shares(cursor):
            raise Exception("ScheduleShare 테이블 수정 실패")
        
        # 2단계: coworker_permissions 테이블 생성
        print("\n2️⃣ coworker_permissions 테이블 생성...")
        if not create_coworker_permissions_table(cursor):
            raise Exception("coworker_permissions 테이블 생성 실패")
        
        # 3단계: 인덱스 생성
        print("\n3️⃣ 성능 인덱스 생성...")
        if not create_indexes(cursor):
            print("⚠️ 인덱스 생성에 실패했지만 계속 진행합니다.")
        
        # 4단계: 기존 데이터 마이그레이션
        print("\n4️⃣ 기존 데이터 마이그레이션...")
        if not migrate_existing_data(cursor):
            raise Exception("기존 데이터 마이그레이션 실패")
        
        # 5단계: 마이그레이션 결과 검증
        print("\n5️⃣ 마이그레이션 결과 검증...")
        if not verify_migration(cursor):
            raise Exception("마이그레이션 검증 실패")
        
        # 변경사항 커밋
        conn.commit()
        print("\n✅ 모든 마이그레이션이 성공적으로 완료되었습니다!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 마이그레이션 중 오류 발생: {e}")
        print("🔍 상세 오류 정보:")
        err = traceback.format_exc()
        print(err)
        
        # 롤백 시도
        try:
            conn.rollback()
            print("🔄 데이터베이스 롤백 완료")
        except:
            print("⚠️ 롤백 실패")
        
        return False
        
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 공동 작업자 기능 데이터베이스 마이그레이션이 완료되었습니다!")
        print("이제 애플리케이션에서 공동 작업자 기능을 사용할 수 있습니다.")
    else:
        print("\n💥 마이그레이션이 실패했습니다.")
        print("백업된 데이터베이스 파일을 확인하고 문제를 해결한 후 다시 시도하세요.")
        sys.exit(1)
