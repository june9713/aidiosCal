#!/usr/bin/env python3
"""
데이터베이스 구조 확인 스크립트
현재 데이터베이스의 테이블과 컬럼 구조를 확인합니다.
"""

import sqlite3
import os

def check_database_structure(db_path):
    """데이터베이스 구조를 확인합니다."""
    
    print("🔍 데이터베이스 구조 확인 중...")
    print(f"📁 데이터베이스: {db_path}")
    print("=" * 50)
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 모든 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"📋 총 테이블 수: {len(tables)}")
        print()
        
        for table_name, in tables:
            print(f"🏷️  테이블: {table_name}")
            
            # 테이블 구조 조회
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print(f"  📊 컬럼 수: {len(columns)}")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                pk_mark = " 🔑" if pk else ""
                not_null_mark = " NOT NULL" if not_null else ""
                default_mark = f" DEFAULT {default_val}" if default_val else ""
                
                print(f"    - {col_name}: {col_type}{not_null_mark}{default_mark}{pk_mark}")
            
            # 테이블의 레코드 수 조회
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  📈 레코드 수: {count}")
            except:
                print(f"  📈 레코드 수: 확인 불가")
            
            print()
        
        # 특정 테이블 상세 확인
        print("🔍 주요 테이블 상세 확인:")
        
        # schedules 테이블 확인
        if any(name == 'schedules' for name, in tables):
            print("\n📅 schedules 테이블:")
            cursor.execute("PRAGMA table_info(schedules)")
            columns = cursor.fetchall()
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                print(f"  - {col_name}: {col_type}")
        
        # quickmemos 테이블 확인
        if any(name == 'quickmemos' for name, in tables):
            print("\n📝 quickmemos 테이블:")
            cursor.execute("PRAGMA table_info(quickmemos)")
            columns = cursor.fetchall()
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                print(f"  - {col_name}: {col_type}")
        
        # memo_attachments 테이블 확인
        if any(name == 'memo_attachments' for name, in tables):
            print("\n📎 memo_attachments 테이블:")
            cursor.execute("PRAGMA table_info(memo_attachments)")
            columns = cursor.fetchall()
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                print(f"  - {col_name}: {col_type}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database_structure("sql_app.db")
