#!/usr/bin/env python3
"""
데이터베이스 상태를 확인하는 스크립트
"""

import sqlite3
import os

def check_database_status():
    """데이터베이스 상태를 종합적으로 확인"""
    if not os.path.exists('sql_app.db'):
        print("❌ sql_app.db 파일이 존재하지 않습니다.")
        return
    
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    print("=== 데이터베이스 상태 확인 ===")
    print(f"데이터베이스 파일: {os.path.abspath('sql_app.db')}")
    print(f"파일 크기: {os.path.getsize('sql_app.db') / 1024:.2f} KB")
    
    # 1. 모든 테이블 목록 확인
    print("\n=== 테이블 목록 ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    # 2. quickmemos 테이블 상세 구조
    print("\n=== quickmemos 테이블 구조 ===")
    try:
        cursor.execute("PRAGMA table_info(quickmemos)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
        
        # 데이터 수 확인
        cursor.execute("SELECT COUNT(*) FROM quickmemos")
        count = cursor.fetchone()[0]
        print(f"  데이터 수: {count}")
        
        if count > 0:
            cursor.execute("SELECT * FROM quickmemos LIMIT 3")
            sample_data = cursor.fetchall()
            print("  샘플 데이터:")
            for row in sample_data:
                print(f"    {row}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 3. memo_attachments 테이블 상세 구조
    print("\n=== memo_attachments 테이블 구조 ===")
    try:
        cursor.execute("PRAGMA table_info(memo_attachments)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
        
        # 데이터 수 확인
        cursor.execute("SELECT COUNT(*) FROM memo_attachments")
        count = cursor.fetchone()[0]
        print(f"  데이터 수: {count}")
        
        if count > 0:
            cursor.execute("SELECT * FROM memo_attachments LIMIT 3")
            sample_data = cursor.fetchall()
            print("  샘플 데이터:")
            for row in sample_data:
                print(f"    {row}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 4. 외래 키 제약 조건 확인
    print("\n=== 외래 키 제약 조건 ===")
    try:
        cursor.execute("PRAGMA foreign_key_list(memo_attachments)")
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            for fk in foreign_keys:
                print(f"  {fk}")
        else:
            print("  외래 키 제약 조건이 없습니다.")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 5. 인덱스 확인
    print("\n=== 인덱스 정보 ===")
    try:
        cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND tbl_name='memo_attachments'")
        indexes = cursor.fetchall()
        if indexes:
            for idx in indexes:
                print(f"  {idx[0]} on {idx[1]}: {idx[2]}")
        else:
            print("  인덱스가 없습니다.")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 6. 스키마 정보 확인
    print("\n=== 스키마 정보 ===")
    try:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='quickmemos'")
        quickmemo_schema = cursor.fetchone()
        if quickmemo_schema:
            print("quickmemos 테이블 생성 SQL:")
            print(f"  {quickmemo_schema[0]}")
        
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='memo_attachments'")
        memo_attachments_schema = cursor.fetchone()
        if memo_attachments_schema:
            print("\nmemo_attachments 테이블 생성 SQL:")
            print(f"  {memo_attachments_schema[0]}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 7. 데이터 무결성 확인
    print("\n=== 데이터 무결성 확인 ===")
    try:
        # quickmemo 타입 첨부파일의 유효한 참조 확인
        cursor.execute("""
            SELECT COUNT(*) FROM memo_attachments ma
            JOIN quickmemos qm ON ma.reference_id = qm.id
            WHERE ma.attachment_type = 'quickmemo'
        """)
        valid_refs = cursor.fetchone()[0]
        print(f"  유효한 quickmemo 참조: {valid_refs}")
        
        # 유효하지 않은 참조 확인
        cursor.execute("""
            SELECT COUNT(*) FROM memo_attachments ma
            WHERE ma.attachment_type = 'quickmemo'
            AND ma.reference_id NOT IN (SELECT id FROM quickmemos)
        """)
        invalid_refs = cursor.fetchone()[0]
        print(f"  유효하지 않은 quickmemo 참조: {invalid_refs}")
        
        # attachment_type별 분포
        cursor.execute("SELECT attachment_type, COUNT(*) FROM memo_attachments GROUP BY attachment_type")
        type_distribution = cursor.fetchall()
        print("  attachment_type 분포:")
        for type_name, count in type_distribution:
            print(f"    {type_name}: {count}")
            
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_database_status()
