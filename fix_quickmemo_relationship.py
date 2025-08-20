#!/usr/bin/env python3
"""
QuickMemo와 MemoAttachment 간의 관계를 수정하는 마이그레이션 스크립트
"""

import sqlite3
import os
from datetime import datetime

def backup_database():
    """데이터베이스 백업 생성"""
    if os.path.exists('sql_app.db'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'sql_app.db.backup_quickmemo_fix_{timestamp}'
        os.system(f'copy sql_app.db {backup_name}')
        print(f"데이터베이스 백업 생성: {backup_name}")
        return backup_name
    return None

def check_table_structure():
    """현재 테이블 구조 확인"""
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    print("=== 현재 테이블 구조 확인 ===")
    
    # quickmemos 테이블 구조
    cursor.execute("PRAGMA table_info(quickmemos)")
    quickmemo_columns = cursor.fetchall()
    print("\nquickmemos 테이블:")
    for col in quickmemo_columns:
        print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
    
    # memo_attachments 테이블 구조
    cursor.execute("PRAGMA table_info(memo_attachments)")
    memo_attachments_columns = cursor.fetchall()
    print("\nmemo_attachments 테이블:")
    for col in memo_attachments_columns:
        print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
    
    # 외래 키 제약 조건 확인
    cursor.execute("PRAGMA foreign_key_list(memo_attachments)")
    foreign_keys = cursor.fetchall()
    print("\nmemo_attachments 외래 키:")
    for fk in foreign_keys:
        print(f"  {fk}")
    
    conn.close()

def fix_relationships():
    """관계 수정을 위한 마이그레이션 실행"""
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    print("\n=== 관계 수정 마이그레이션 시작 ===")
    
    try:
        # 1. 기존 인덱스 확인 및 삭제 (필요시)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='memo_attachments'")
        existing_indexes = cursor.fetchall()
        print(f"기존 인덱스: {existing_indexes}")
        
        # 2. 테이블 구조 확인
        cursor.execute("PRAGMA table_info(memo_attachments)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'reference_id' not in column_names:
            print("ERROR: reference_id 컬럼이 존재하지 않습니다.")
            return False
            
        if 'attachment_type' not in column_names:
            print("ERROR: attachment_type 컬럼이 존재하지 않습니다.")
            return False
        
        # 3. 데이터 무결성 확인
        cursor.execute("SELECT COUNT(*) FROM memo_attachments WHERE attachment_type = 'quickmemo'")
        quickmemo_count = cursor.fetchone()[0]
        print(f"quickmemo 타입 첨부파일 수: {quickmemo_count}")
        
        if quickmemo_count > 0:
            # 4. quickmemo 타입 첨부파일의 reference_id가 유효한지 확인
            cursor.execute("""
                SELECT ma.id, ma.reference_id, ma.attachment_type 
                FROM memo_attachments ma 
                WHERE ma.attachment_type = 'quickmemo' 
                AND ma.reference_id NOT IN (SELECT id FROM quickmemos)
            """)
            invalid_references = cursor.fetchall()
            
            if invalid_references:
                print(f"경고: 유효하지 않은 quickmemo 참조가 {len(invalid_references)}개 있습니다:")
                for ref in invalid_references:
                    print(f"  ID: {ref[0]}, reference_id: {ref[1]}, type: {ref[2]}")
                
                # 유효하지 않은 참조를 가진 첨부파일 삭제 또는 수정
                print("유효하지 않은 참조를 가진 첨부파일을 삭제합니다...")
                cursor.execute("""
                    DELETE FROM memo_attachments 
                    WHERE attachment_type = 'quickmemo' 
                    AND reference_id NOT IN (SELECT id FROM quickmemos)
                """)
                print(f"삭제된 행 수: {cursor.rowcount}")
        
        # 5. 인덱스 생성 (성능 향상을 위해)
        print("인덱스 생성 중...")
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memo_attachments_reference_type ON memo_attachments(reference_id, attachment_type)")
            print("인덱스 생성 완료")
        except Exception as e:
            print(f"인덱스 생성 중 오류 (무시됨): {e}")
        
        # 6. 변경사항 커밋
        conn.commit()
        print("마이그레이션 완료!")
        
        return True
        
    except Exception as e:
        print(f"마이그레이션 중 오류 발생: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_migration():
    """마이그레이션 결과 검증"""
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    print("\n=== 마이그레이션 결과 검증 ===")
    
    # quickmemo 타입 첨부파일 수 확인
    cursor.execute("SELECT COUNT(*) FROM memo_attachments WHERE attachment_type = 'quickmemo'")
    quickmemo_count = cursor.fetchone()[0]
    print(f"quickmemo 타입 첨부파일 수: {quickmemo_count}")
    
    # 유효한 참조 확인
    cursor.execute("""
        SELECT COUNT(*) FROM memo_attachments ma
        JOIN quickmemos qm ON ma.reference_id = qm.id
        WHERE ma.attachment_type = 'quickmemo'
    """)
    valid_references = cursor.fetchone()[0]
    print(f"유효한 quickmemo 참조 수: {valid_references}")
    
    # 인덱스 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='memo_attachments'")
    indexes = cursor.fetchall()
    print(f"memo_attachments 인덱스: {[idx[0] for idx in indexes]}")
    
    conn.close()

def main():
    """메인 실행 함수"""
    print("QuickMemo 관계 수정 마이그레이션 시작")
    print("=" * 50)
    
    # 1. 데이터베이스 백업
    backup_file = backup_database()
    
    # 2. 현재 구조 확인
    check_table_structure()
    
    # 3. 마이그레이션 실행
    if fix_relationships():
        # 4. 결과 검증
        verify_migration()
        print("\n✅ 마이그레이션이 성공적으로 완료되었습니다!")
    else:
        print("\n❌ 마이그레이션에 실패했습니다.")
        if backup_file:
            print(f"백업 파일 {backup_file}에서 복원할 수 있습니다.")

if __name__ == "__main__":
    main()
