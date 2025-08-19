import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def migrate_database():
    """수동으로 데이터베이스를 마이그레이션합니다."""
    try:
        # sql_app.db 연결
        conn = sqlite3.connect('sql_app.db')
        cursor = conn.cursor()
        
        # 기존 테이블의 컬럼 정보 확인
        def table_has_column(table_name, column_name):
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            return any(column[1] == column_name for column in columns)
        
        # Schedule 테이블에 is_deleted 컬럼 추가
        if not table_has_column('schedules', 'is_deleted'):
            logger.info("Adding is_deleted column to schedules table...")
            cursor.execute('''
                ALTER TABLE schedules
                ADD COLUMN is_deleted BOOLEAN DEFAULT 0
            ''')
            logger.info("Successfully added is_deleted column to schedules table")
        
        # Alarm 테이블 필드 추가
        alarm_columns = [
            ('is_deleted', 'BOOLEAN DEFAULT 0'),
            ('is_activated', 'BOOLEAN DEFAULT 0'),
            ('activated_at', 'TIMESTAMP'),
        ]
        
        for column_name, column_type in alarm_columns:
            if not table_has_column('alarms', column_name):
                logger.info(f"Adding {column_name} column to alarms table...")
                cursor.execute(f'''
                    ALTER TABLE alarms
                    ADD COLUMN {column_name} {column_type}
                ''')
                logger.info(f"Successfully added {column_name} column to alarms table")
        
        # 기존 is_read 필드 제거 (SQLite는 DROP COLUMN을 지원하지 않으므로 무시)
        
        # 변경사항 저장
        conn.commit()
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 마이그레이션 실행
    migrate_database() 