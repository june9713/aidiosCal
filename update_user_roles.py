#!/usr/bin/env python3
"""
사용자 역할 업데이트 스크립트
데이터베이스에 role 필드가 없거나 기본값인 사용자들의 역할을 설정합니다.
"""

import sqlite3
import os

def update_user_roles():
    # 데이터베이스 파일 경로
    db_path = "sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 현재 사용자 테이블 구조 확인
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("현재 users 테이블 컬럼:", column_names)
        
        # role 컬럼이 없으면 추가
        if 'role' not in column_names:
            print("role 컬럼을 추가합니다...")
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            conn.commit()
            print("role 컬럼이 추가되었습니다.")
        
        # 현재 사용자들의 role 확인
        cursor.execute("SELECT id, username, name, role FROM users")
        users = cursor.fetchall()
        
        print("\n현재 사용자 목록:")
        for user in users:
            print(f"ID: {user[0]}, Username: {user[1]}, Name: {user[2]}, Role: {user[3]}")
        
        # 특정 사용자들의 역할 설정
        role_updates = [
            ("june9713", "admin"),  # 박정준을 admin으로 설정
            ("pci8099", "manager"), # 박찬일을 manager로 설정
        ]
        
        print("\n사용자 역할을 업데이트합니다...")
        for username, role in role_updates:
            cursor.execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
            if cursor.rowcount > 0:
                print(f"{username}의 역할을 {role}로 설정했습니다.")
            else:
                print(f"{username} 사용자를 찾을 수 없습니다.")
        
        conn.commit()
        
        # 업데이트 후 사용자 목록 확인
        print("\n업데이트 후 사용자 목록:")
        cursor.execute("SELECT id, username, name, role FROM users")
        users = cursor.fetchall()
        for user in users:
            print(f"ID: {user[0]}, Username: {user[1]}, Name: {user[2]}, Role: {user[3]}")
        
        print("\n사용자 역할 업데이트가 완료되었습니다.")
        
    except sqlite3.Error as e:
        print(f"데이터베이스 오류: {e}")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_user_roles()
