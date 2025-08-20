#!/usr/bin/env python3
"""
memo_attachments 테이블 스키마를 모델과 일치하도록 수정하는 마이그레이션 스크립트
"""

import sqlite3
import os
from datetime import datetime

def backup_database():
    """데이터베이스 백업 생성"""
    if os.path.exists('sql_app.db'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'sql_app.db.backup_schema_fix_{timestamp}'
        os.system(f'copy sql_app.db {backup_name}')
        print(f"데이터베이스 백업 생성: {backup_name}")
        return backup_name
    return None

def check_current_schema():
    """현재 스키마 상태 확인"""
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    print("=== 현재 스키마 상태 확인 ===")
    
    # memo_attachments 테이블 구조
    cursor.execute("PRAGMA table_info(memo_attachments)")
    columns = cursor.fetchall()
    print("\nmemo_attachments 테이블 컬럼:")
    for col in columns:
        print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
    
    # 외래 키 제약 조건
    cursor.execute("PRAGMA foreign_key_list(memo_attachments)")
    foreign_keys = cursor.fetchall()
    print("\n외래 키 제약 조건:")
    for fk in foreign_keys:
        print(f"  {fk}")
    
    conn.close()

def fix_schema():
    """스키마 수정 실행"""
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    print("\n=== 스키마 수정 시작 ===")
    
    try:
        # 1. 기존 데이터 백업
        print("기존 데이터 백업 중...")
        cursor.execute("CREATE TABLE memo_attachments_backup AS SELECT * FROM memo_attachments")
        print("백업 테이블 생성 완료")
        
        # 2. 기존 테이블 삭제
        print("기존 테이블 삭제 중...")
        cursor.execute("DROP TABLE memo_attachments")
        print("기존 테이블 삭제 완료")
        
        # 3. 새로운 테이블 생성 (모델과 일치)
        print("새로운 테이블 생성 중...")
        create_table_sql = """
        CREATE TABLE memo_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            attachment_type TEXT NOT NULL,
            reference_id INTEGER NOT NULL,
            uploader_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploader_id) REFERENCES users (id)
        )
        """
        cursor.execute(create_table_sql)
        print("새로운 테이블 생성 완료")
        
        # 4. 인덱스 생성
        print("인덱스 생성 중...")
        cursor.execute("CREATE INDEX idx_memo_attachments_reference_type ON memo_attachments(reference_id, attachment_type)")
        cursor.execute("CREATE INDEX idx_memo_attachments_attachment_type ON memo_attachments(attachment_type)")
        cursor.execute("CREATE INDEX idx_memo_attachments_reference_id ON memo_attachments(reference_id)")
        print("인덱스 생성 완료")
        
        # 5. 데이터 복원 (uploader_id 컬럼이 없는 경우 기본값 설정)
        print("데이터 복원 중...")
        cursor.execute("""
            INSERT INTO memo_attachments (
                filename, file_path, file_size, mime_type, 
                attachment_type, reference_id, uploader_id, created_at
            )
            SELECT 
                filename, file_path, file_size, mime_type,
                attachment_type, reference_id, 
                COALESCE(uploader_id, 1) as uploader_id,  -- uploader_id가 없으면 기본값 1
                created_at
            FROM memo_attachments_backup
        """)
        
        restored_count = cursor.rowcount
        print(f"복원된 데이터 수: {restored_count}")
        
        # 6. 백업 테이블 삭제
        print("백업 테이블 삭제 중...")
        cursor.execute("DROP TABLE memo_attachments_backup")
        print("백업 테이블 삭제 완료")
        
        # 7. 변경사항 커밋
        conn.commit()
        print("스키마 수정 완료!")
        
        return True
        
    except Exception as e:
        print(f"스키마 수정 중 오류 발생: {e}")
        conn.rollback()
        
        # 롤백 시 백업 테이블에서 복원 시도
        try:
            print("롤백 중... 백업 테이블에서 복원 시도...")
            if cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memo_attachments_backup'").fetchone():
                cursor.execute("DROP TABLE IF EXISTS memo_attachments")
                cursor.execute("CREATE TABLE memo_attachments AS SELECT * FROM memo_attachments_backup")
                cursor.execute("DROP TABLE memo_attachments_backup")
                conn.commit()
                print("백업 테이블에서 복원 완료")
        except Exception as restore_error:
            print(f"백업 복원 중 오류: {restore_error}")
        
        return False
    finally:
        conn.close()

def verify_schema():
    """스키마 수정 결과 검증"""
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    print("\n=== 스키마 수정 결과 검증 ===")
    
    # 테이블 구조 확인
    cursor.execute("PRAGMA table_info(memo_attachments)")
    columns = cursor.fetchall()
    print("\n수정된 memo_attachments 테이블 컬럼:")
    for col in columns:
        print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
    
    # 외래 키 제약 조건 확인
    cursor.execute("PRAGMA foreign_key_list(memo_attachments)")
    foreign_keys = cursor.fetchall()
    print("\n외래 키 제약 조건:")
    for fk in foreign_keys:
        print(f"  {fk}")
    
    # 인덱스 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='memo_attachments'")
    indexes = cursor.fetchall()
    print(f"\n인덱스: {[idx[0] for idx in indexes]}")
    
    # 데이터 수 확인
    cursor.execute("SELECT COUNT(*) FROM memo_attachments")
    count = cursor.fetchone()[0]
    print(f"\n데이터 수: {count}")
    
    # 데이터 샘플 확인
    if count > 0:
        cursor.execute("SELECT * FROM memo_attachments LIMIT 2")
        sample_data = cursor.fetchall()
        print("\n샘플 데이터:")
        for row in sample_data:
            print(f"  {row}")
    
    conn.close()

def main():
    """메인 실행 함수"""
    print("memo_attachments 스키마 수정 마이그레이션 시작")
    print("=" * 60)
    
    # 1. 데이터베이스 백업
    backup_file = backup_database()
    
    # 2. 현재 스키마 확인
    check_current_schema()
    
    # 3. 스키마 수정 실행
    if fix_schema():
        # 4. 결과 검증
        verify_schema()
        print("\n✅ 스키마 수정이 성공적으로 완료되었습니다!")
    else:
        print("\n❌ 스키마 수정에 실패했습니다.")
        if backup_file:
            print(f"백업 파일 {backup_file}에서 복원할 수 있습니다.")

if __name__ == "__main__":
    main()
