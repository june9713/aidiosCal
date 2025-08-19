#!/usr/bin/env python3
"""
수동 DB 마이그레이션: Schedule 테이블에 individual 컬럼 추가
"""

import sqlite3
from pathlib import Path

def migrate_add_individual_column():
    """Schedule 테이블에 individual 컬럼을 추가합니다."""
    
    db_path = "sql_app.db"
    
    # 데이터베이스 파일이 존재하는지 확인
    if not Path(db_path).exists():
        print(f"데이터베이스 파일 {db_path}이 존재하지 않습니다.")
        return False
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 현재 스키마 확인
        cursor.execute("PRAGMA table_info(schedules)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("현재 schedules 테이블 컬럼들:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # individual 컬럼이 이미 존재하는지 확인
        if 'individual' in column_names:
            print("\n⚠️  'individual' 컬럼이 이미 존재합니다. 마이그레이션을 건너뜁니다.")
            return True
        
        # individual 컬럼 추가
        print("\n📝 'individual' 컬럼을 추가합니다...")
        cursor.execute("""
            ALTER TABLE schedules 
            ADD COLUMN individual BOOLEAN DEFAULT 0
        """)
        
        # 변경사항 커밋
        conn.commit()
        
        # 결과 확인
        cursor.execute("PRAGMA table_info(schedules)")
        new_columns = cursor.fetchall()
        
        print("\n✅ 마이그레이션 완료! 업데이트된 schedules 테이블 컬럼들:")
        for col in new_columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # 기존 데이터 개수 확인
        cursor.execute("SELECT COUNT(*) FROM schedules")
        count = cursor.fetchone()[0]
        print(f"\n📊 총 {count}개의 기존 일정이 있습니다. (모두 individual=0으로 설정됨)")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ 데이터베이스 오류: {e}")
        return False
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Schedule 테이블 individual 컬럼 추가 마이그레이션을 시작합니다...")
    success = migrate_add_individual_column()
    
    if success:
        print("\n🎉 마이그레이션이 성공적으로 완료되었습니다!")
        print("💡 이제 애플리케이션을 다시 시작할 수 있습니다.")
    else:
        print("\n💥 마이그레이션이 실패했습니다. 오류를 확인해주세요.") 