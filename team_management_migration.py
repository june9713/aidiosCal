#!/usr/bin/env python3
"""
팀 관리 시스템 마이그레이션 스크립트
- teams, team_members, team_invitations 테이블 생성
-  팀 기본 생성 (초대코드: aidios1111)
"""

import sqlite3
import os
import uuid
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

def create_backup():
    """데이터베이스 백업 생성"""
    try:
        import shutil
        from datetime import datetime
        
        db_path = get_db_path()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_team_mgmt_{timestamp}"
        
        shutil.copy2(db_path, backup_path)
        print(f"✅ 백업 생성됨: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ 백업 생성 실패: {e}")
        return False

def get_admin_user_id(cursor):
    """관리자 사용자 ID 조회"""
    cursor.execute("SELECT id FROM users WHERE username = 'admin' LIMIT 1")
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # admin이 없으면 첫 번째 사용자
    cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
    result = cursor.fetchone()
    return result[0] if result else None

def create_team_management_tables():
    """팀 관리 테이블들 생성"""
    
    if not check_database_exists():
        return False
    
    db_path = get_db_path()
    print(f"📂 데이터베이스 경로: {db_path}")
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. teams 테이블 생성
        print("🔧 teams 테이블 생성 중...")
        if not check_table_exists(cursor, "teams"):
            cursor.execute("""
                CREATE TABLE teams (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    description TEXT,
                    invite_code VARCHAR UNIQUE NOT NULL,
                    leader_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (leader_id) REFERENCES users (id)
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX idx_teams_name ON teams(name)")
            cursor.execute("CREATE UNIQUE INDEX idx_teams_invite_code ON teams(invite_code)")
            cursor.execute("CREATE INDEX idx_teams_leader ON teams(leader_id)")
            print("✅ teams 테이블 생성 완료")
        else:
            print("⚠️  teams 테이블이 이미 존재합니다")
        
        # 2. team_members 테이블 생성
        print("🔧 team_members 테이블 생성 중...")
        if not check_table_exists(cursor, "team_members"):
            cursor.execute("""
                CREATE TABLE team_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id VARCHAR NOT NULL,
                    user_id INTEGER NOT NULL,
                    role VARCHAR DEFAULT 'member',
                    status VARCHAR DEFAULT 'pending',
                    joined_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(team_id, user_id)
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX idx_team_members_team ON team_members(team_id)")
            cursor.execute("CREATE INDEX idx_team_members_user ON team_members(user_id)")
            cursor.execute("CREATE INDEX idx_team_members_status ON team_members(status)")
            print("✅ team_members 테이블 생성 완료")
        else:
            print("⚠️  team_members 테이블이 이미 존재합니다")
        
        # 3. team_invitations 테이블 생성
        print("🔧 team_invitations 테이블 생성 중...")
        if not check_table_exists(cursor, "team_invitations"):
            cursor.execute("""
                CREATE TABLE team_invitations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id VARCHAR NOT NULL,
                    user_id INTEGER NOT NULL,
                    invite_code VARCHAR NOT NULL,
                    status VARCHAR DEFAULT 'pending',
                    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    processed_by INTEGER,
                    FOREIGN KEY (team_id) REFERENCES teams (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (processed_by) REFERENCES users (id)
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX idx_team_invitations_team ON team_invitations(team_id)")
            cursor.execute("CREATE INDEX idx_team_invitations_user ON team_invitations(user_id)")
            cursor.execute("CREATE INDEX idx_team_invitations_status ON team_invitations(status)")
            print("✅ team_invitations 테이블 생성 완료")
        else:
            print("⚠️  team_invitations 테이블이 이미 존재합니다")
        
        # 4. AIDIOS 팀 생성
        print("🔧 AIDIOS 기본 팀 생성 중...")
        
        # AIDIOS 팀이 이미 있는지 확인
        cursor.execute("SELECT id FROM teams WHERE invite_code = 'aidios1111'")
        aidios_team = cursor.fetchone()
        
        if not aidios_team:
            # 관리자 사용자 조회
            admin_user_id = get_admin_user_id(cursor)
            if not admin_user_id:
                print("❌ 관리자 사용자를 찾을 수 없습니다. 먼저 사용자를 생성해주세요.")
                conn.close()
                return False
            
            # AIDIOS 팀 생성
            aidios_team_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO teams (id, name, description, invite_code, leader_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                aidios_team_id,
                "AIDIOS",
                "기본 AIDIOS 팀",
                "aidios1111",
                admin_user_id
            ))
            
            # 관리자를 팀 리더로 추가
            cursor.execute("""
                INSERT INTO team_members (team_id, user_id, role, status, joined_at)
                VALUES (?, ?, 'leader', 'approved', CURRENT_TIMESTAMP)
            """, (aidios_team_id, admin_user_id))
            
            print(f"✅ AIDIOS 팀 생성 완료 (ID: {aidios_team_id})")
        else:
            print("⚠️  AIDIOS 팀이 이미 존재합니다")
        
        # 변경사항 커밋
        conn.commit()
        
        # 결과 확인
        print("\n🔍 생성된 팀 확인...")
        cursor.execute("""
            SELECT t.name, t.invite_code, u.name as leader_name, 
                   COUNT(tm.id) as member_count
            FROM teams t
            JOIN users u ON t.leader_id = u.id
            LEFT JOIN team_members tm ON t.id = tm.team_id AND tm.status = 'approved'
            GROUP BY t.id, t.name, t.invite_code, u.name
            ORDER BY t.created_at
        """)
        teams = cursor.fetchall()
        
        for team in teams:
            print(f"  팀: {team[0]} | 코드: {team[1]} | 리더: {team[2]} | 멤버: {team[3]}명")
        
        conn.close()
        print("\n✅ 팀 관리 시스템 테이블 생성 완료!")
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

def main():
    """메인 함수"""
    print("=" * 70)
    print("🗃️  팀 관리 시스템 마이그레이션")
    print("=" * 70)
    
    print("📋 작업 내용:")
    print("   - teams 테이블 생성 (팀 정보)")
    print("   - team_members 테이블 생성 (팀원 정보)")
    print("   - team_invitations 테이블 생성 (가입 요청)")
    print("   - AIDIOS 기본 팀 생성 (초대코드: aidios1111)")
    print("   - 인덱스 생성")
    print()
    
    # 백업 생성
    print("1️⃣  데이터베이스 백업 생성...")
    if not create_backup():
        print("❌ 백업 생성에 실패했습니다. 마이그레이션을 중단합니다.")
        return
    
    # 마이그레이션 실행
    print("\n2️⃣  마이그레이션 실행...")
    if create_team_management_tables():
        print("\n🎉 팀 관리 시스템 마이그레이션이 성공적으로 완료되었습니다!")
        print("\n📋 사용법:")
        print("   1. 팀 생성: POST /teams")
        print("   2. 팀 가입: POST /teams/join (초대코드 사용)")
        print("   3. 팀원 관리: POST /teams/{team_id}/manage-member")
        print("   4. AIDIOS 팀 초대코드: aidios1111")
        print("\n🔗 API 엔드포인트:")
        print("   - GET /teams - 내 팀 목록")
        print("   - POST /teams - 새 팀 생성")
        print("   - POST /teams/join - 팀 가입 요청")
        print("   - GET /teams/{team_id} - 팀 상세 정보")
        print("   - GET /teams/{team_id}/members - 팀원 목록")
        print("   - GET /teams/{team_id}/pending-requests - 가입 대기 목록")
        print("   - POST /teams/{team_id}/manage-member - 팀원 관리")
    else:
        print("\n❌ 마이그레이션 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main() 