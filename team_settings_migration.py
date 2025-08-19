#!/usr/bin/env python3
"""
팀 설정 테이블 생성 마이그레이션 스크립트
- team_settings 테이블 생성
- 기본 팀 설정 데이터 초기화
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
    """데이터베이스 파일 존재 확인"""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 존재하지 않습니다: {db_path}")
        return False
    return True

def check_table_exists(cursor, table_name):
    """테이블 존재 여부 확인"""
    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone()[0] > 0

def create_team_settings_table():
    """팀 설정 테이블 생성 및 초기 데이터 설정"""
    
    if not check_database_exists():
        return False
    
    db_path = get_db_path()
    print(f"📂 데이터베이스 경로: {db_path}")
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 team_settings 테이블 존재 여부 확인...")
        
        if check_table_exists(cursor, "team_settings"):
            print("⚠️  team_settings 테이블이 이미 존재합니다.")
            
            # 기존 데이터 확인
            cursor.execute("SELECT COUNT(*) FROM team_settings")
            count = cursor.fetchone()[0]
            print(f"현재 팀 설정 개수: {count}")
            
            if count == 0:
                print("🔧 기본 팀 설정 데이터 추가...")
                insert_default_team_settings(cursor)
                conn.commit()
            
            conn.close()
            return True
        
        print("🔧 team_settings 테이블 생성 중...")
        
        # 팀 설정 테이블 생성
        cursor.execute("""
            CREATE TABLE team_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_slot VARCHAR UNIQUE NOT NULL,
                team_name VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("✅ team_settings 테이블 생성 완료")
        
        # 인덱스 생성
        cursor.execute("CREATE UNIQUE INDEX idx_team_slot ON team_settings(team_slot)")
        print("✅ 인덱스 생성 완료")
        
        # 기본 팀 설정 데이터 추가
        print("🔧 기본 팀 설정 데이터 추가...")
        insert_default_team_settings(cursor)
        
        # 변경사항 커밋
        conn.commit()
        
        # 결과 확인
        print("\n🔍 생성된 팀 설정 확인...")
        cursor.execute("SELECT team_slot, team_name FROM team_settings ORDER BY team_slot")
        team_settings = cursor.fetchall()
        for setting in team_settings:
            team_name_display = setting[1] if setting[1] else "(설정 안됨)"
            print(f"  {setting[0]}: {team_name_display}")
        
        conn.close()
        print("\n✅ team_settings 테이블 생성 및 초기화 완료!")
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

def insert_default_team_settings(cursor):
    """기본 팀 설정 데이터 삽입"""
    # team1은 AIDIOS로, 나머지는 NULL로 설정
    team_settings = []
    for i in range(1, 11):
        team_slot = f"team{i}"
        team_name = "AIDIOS" if i == 1 else None
        team_settings.append((team_slot, team_name))
    
    cursor.executemany("""
        INSERT OR IGNORE INTO team_settings (team_slot, team_name)
        VALUES (?, ?)
    """, team_settings)
    
    print(f"  ✅ {len(team_settings)}개의 기본 팀 설정 추가됨")

def main():
    """메인 함수"""
    print("=" * 60)
    print("🗃️  팀 설정 테이블 생성 마이그레이션")
    print("=" * 60)
    
    print("📋 작업 내용:")
    print("   - team_settings 테이블 생성")
    print("   - team1 슬롯을 'AIDIOS'로 설정")
    print("   - team2~team10 슬롯을 비워둠")
    print("   - 인덱스 생성")
    print()
    
    # 마이그레이션 실행
    if create_team_settings_table():
        print("\n🎉 팀 설정 테이블 마이그레이션이 성공적으로 완료되었습니다!")
        print("\n📋 사용법:")
        print("   1. 웹 인터페이스에서 '팀 관리' 버튼 클릭")
        print("   2. team1~team10 슬롯에 원하는 팀 이름 입력")
        print("   3. 사용자는 설정된 팀만 선택 가능")
        print("   4. 비어있는 슬롯은 사용자 선택 목록에 나타나지 않음")
    else:
        print("\n❌ 마이그레이션 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main() 