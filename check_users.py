#!/usr/bin/env python3
"""
사용자 테이블과 role 정보를 확인하는 스크립트
"""

import sqlite3
import os

def check_users_table():
    """사용자 테이블 구조와 role 정보 확인"""
    if not os.path.exists('sql_app.db'):
        print("❌ sql_app.db 파일이 존재하지 않습니다.")
        return
    
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    
    print("=== 데이터베이스 상태 확인 ===")
    print(f"데이터베이스 파일: {os.path.abspath('sql_app.db')}")
    
    # 1. 모든 테이블 목록 확인
    print("\n=== 테이블 목록 ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    # 2. users 테이블 구조 확인
    print("\n=== users 테이블 구조 ===")
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
        
        # 데이터 수 확인
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        print(f"  데이터 수: {count}")
        
        if count > 0:
            cursor.execute("SELECT * FROM users LIMIT 5")
            sample_data = cursor.fetchall()
            print("  샘플 데이터:")
            for row in sample_data:
                print(f"    {row}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 3. 특정 사용자 확인 (june9713, pci8099)
    print("\n=== 특정 사용자 확인 ===")
    try:
        cursor.execute("SELECT * FROM users WHERE username IN ('june9713', 'pci8099')")
        users = cursor.fetchall()
        if users:
            print("june9713, pci8099 사용자:")
            for user in users:
                print(f"  {user}")
        else:
            print("해당 사용자를 찾을 수 없습니다.")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 4. role 컬럼이 있는지 확인
    print("\n=== role 컬럼 확인 ===")
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        role_exists = any(col[1] == 'role' for col in columns)
        print(f"role 컬럼 존재: {role_exists}")
        
        if role_exists:
            cursor.execute("SELECT username, role FROM users WHERE username IN ('june9713', 'pci8099')")
            roles = cursor.fetchall()
            print("사용자별 role:")
            for username, role in roles:
                print(f"  {username}: {role}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    # 5. users 테이블 스키마 확인
    print("\n=== users 테이블 스키마 ===")
    try:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        schema = cursor.fetchone()
        if schema:
            print("users 테이블 생성 SQL:")
            print(f"  {schema[0]}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_users_table()
