#!/usr/bin/env python3
"""
pci8099 사용자의 role을 admin으로 변경하는 스크립트
"""

import sqlite3
import os

def update_pci8099_role():
    """pci8099 사용자의 role을 admin으로 변경"""
    db_path = "sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 현재 pci8099 사용자의 role 확인
        cursor.execute("SELECT id, username, name, role FROM users WHERE username = 'pci8099'")
        user = cursor.fetchone()
        
        if not user:
            print("pci8099 사용자를 찾을 수 없습니다.")
            return
        
        print(f"현재 pci8099 사용자 정보:")
        print(f"  ID: {user[0]}, Username: {user[1]}, Name: {user[2]}, Role: {user[3]}")
        
        # role을 admin으로 변경
        cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'pci8099'")
        conn.commit()
        
        print("pci8099 사용자의 role이 admin으로 변경되었습니다.")
        
        # 변경된 정보 확인
        cursor.execute("SELECT id, username, name, role FROM users WHERE username = 'pci8099'")
        updated_user = cursor.fetchone()
        print(f"변경된 pci8099 사용자 정보:")
        print(f"  ID: {updated_user[0]}, Username: {updated_user[1]}, Name: {updated_user[2]}, Role: {updated_user[3]}")
        
        # 전체 사용자 목록 확인
        print("\n전체 사용자 목록:")
        cursor.execute("SELECT username, name, role FROM users ORDER BY id")
        users = cursor.fetchall()
        for username, name, role in users:
            print(f"  {username} ({name}): {role}")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    update_pci8099_role()
