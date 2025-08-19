#!/usr/bin/env python3
"""
사용자 테이블 필드 추가 마이그레이션 스크립트
- email, nickname, address, team, phone1, phone2, phone3, fax 필드 추가
- 기존 사용자들의 team을 "AIDIOS"로 설정
"""

import sqlite3
import os
from pathlib import Path

def get_db_path():
    """데이터베이스 파일 경로 반환"""
    current_dir = Path(__file__).parent
    db_path = current_dir / "sql_app.db"
    return str(db_path)

def check_database_exists():
    """데이터베이스 파일 존재 여부 확인"""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return False
    return True

def check_column_exists(cursor, table_name, column_name):
    """테이블에 컬럼이 존재하는지 확인"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def add_user_fields_migration():
    """사용자 테이블에 새로운 필드들 추가"""
    
    if not check_database_exists():
        return False
    
    db_path = get_db_path()
    print(f"📂 데이터베이스 경로: {db_path}")
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 현재 사용자 테이블 구조 확인...")
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = cursor.fetchall()
        print("기존 컬럼들:")
        for col in existing_columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # 추가할 새로운 필드들
        new_fields = [
            ("email", "VARCHAR"),
            ("nickname", "VARCHAR"),
            ("address", "VARCHAR"), 
            ("team", "VARCHAR"),
            ("phone1", "VARCHAR"),
            ("phone2", "VARCHAR"),
            ("phone3", "VARCHAR"),
            ("fax", "VARCHAR")
        ]
        
        print("\n🔧 새로운 필드들 추가 중...")
        
        # 각 필드를 하나씩 추가
        for field_name, field_type in new_fields:
            if not check_column_exists(cursor, "users", field_name):
                print(f"  ➕ {field_name} 필드 추가...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
                print(f"     ✅ {field_name} 필드 추가 완료")
            else:
                print(f"  ⚠️  {field_name} 필드가 이미 존재합니다")
        
        # 기존 사용자들의 team을 "AIDIOS"로 설정
        print("\n👥 기존 사용자들의 팀 설정...")
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"현재 등록된 사용자 수: {user_count}")
        
        if user_count > 0:
            # team 필드가 NULL이거나 빈 문자열인 사용자들을 "AIDIOS"로 설정
            cursor.execute("""
                UPDATE users 
                SET team = 'AIDIOS' 
                WHERE team IS NULL OR team = ''
            """)
            updated_count = cursor.rowcount
            print(f"  ✅ {updated_count}명의 사용자 팀을 'AIDIOS'로 설정 완료")
        
        # 변경사항 커밋
        conn.commit()
        
        print("\n🔍 마이그레이션 후 테이블 구조 확인...")
        cursor.execute("PRAGMA table_info(users)")
        updated_columns = cursor.fetchall()
        print("업데이트된 컬럼들:")
        for col in updated_columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # 사용자 데이터 확인
        print("\n👥 사용자 데이터 확인...")
        cursor.execute("SELECT id, username, name, team FROM users")
        users = cursor.fetchall()
        for user in users:
            print(f"  사용자 ID: {user[0]}, 이름: {user[1]} ({user[2]}), 팀: {user[3]}")
        
        conn.close()
        print("\n✅ 마이그레이션 완료!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ 데이터베이스 오류: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def create_backup():
    """데이터베이스 백업 생성"""
    db_path = get_db_path()
    backup_path = db_path.replace('.db', '_backup_before_migration.db')
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"📦 백업 생성 완료: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ 백업 생성 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("=" * 60)
    print("🗃️  사용자 테이블 필드 추가 마이그레이션")
    print("=" * 60)
    
    # 백업 생성
    print("1️⃣  데이터베이스 백업 생성...")
    if not create_backup():
        print("❌ 백업 생성에 실패했습니다. 마이그레이션을 중단합니다.")
        return
    
    # 마이그레이션 실행
    print("\n2️⃣  마이그레이션 실행...")
    if add_user_fields_migration():
        print("\n🎉 모든 마이그레이션이 성공적으로 완료되었습니다!")
        print("\n📋 추가된 필드들:")
        print("   - email: 이메일 주소")
        print("   - nickname: 닉네임") 
        print("   - address: 주소")
        print("   - team: 팀명 (기본값: AIDIOS)")
        print("   - phone1, phone2, phone3: 전화번호들")
        print("   - fax: 팩스번호")
        print("\n🎯 팀 시스템:")
        print("   - 사용 가능한 팀: team1, team2, team3, ..., team10")
        print("   - 현재 사용자들은 모두 'AIDIOS' 팀으로 설정됨")
        print("   - 팀은 추가적인 필터링 기능으로 사용됩니다")
    else:
        print("\n❌ 마이그레이션 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main() 