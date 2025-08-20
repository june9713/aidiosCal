#!/usr/bin/env python3
"""
메모 첨부파일 테이블 마이그레이션 스크립트
기존 JSON 형태로 저장된 첨부파일 정보를 새로운 테이블로 마이그레이션합니다.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

def create_memo_attachments_table(db_path):
    """메모 첨부파일 테이블을 생성합니다."""
    
    print("🔧 메모 첨부파일 테이블 생성 중...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 테이블이 이미 존재하는지 확인
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='memo_attachments'
        """)
        
        if cursor.fetchone():
            print("ℹ️  memo_attachments 테이블이 이미 존재합니다.")
            return True
        
        # 테이블 생성
        cursor.execute("""
            CREATE TABLE memo_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                attachment_type TEXT NOT NULL,
                reference_id INTEGER NOT NULL,
                uploader_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploader_id) REFERENCES users (id)
            )
        """)
        
        # 인덱스 생성
        cursor.execute("""
            CREATE INDEX idx_memo_attachments_attachment_type 
            ON memo_attachments (attachment_type)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_memo_attachments_reference_id 
            ON memo_attachments (reference_id)
        """)
        
        conn.commit()
        print("✅ memo_attachments 테이블 생성 완료")
        return True
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def migrate_existing_data(db_path):
    """기존 JSON 형태의 첨부파일 데이터를 새로운 테이블로 마이그레이션합니다."""
    
    print("🔄 기존 데이터 마이그레이션 중...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 스케줄 메모의 첨부파일 정보 마이그레이션
        print("📅 스케줄 메모 첨부파일 마이그레이션...")
        
        # memo_extra 필드에 JSON 데이터가 있는 스케줄 조회
        cursor.execute("""
            SELECT id, memo_extra, owner_id 
            FROM schedules 
            WHERE memo_extra IS NOT NULL 
            AND memo_extra != '' 
            AND memo_extra != 'null'
        """)
        
        schedule_files = cursor.fetchall()
        migrated_schedules = 0
        
        for schedule_id, memo_extra, owner_id in schedule_files:
            try:
                # JSON 파싱
                files_data = json.loads(memo_extra)
                if isinstance(files_data, list) and files_data:
                    for file_info in files_data:
                        if isinstance(file_info, dict) and 'filename' in file_info:
                            cursor.execute("""
                                INSERT INTO memo_attachments 
                                (filename, file_path, file_size, mime_type, attachment_type, reference_id, uploader_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                file_info.get('filename', ''),
                                file_info.get('filepath', ''),
                                file_info.get('filesize', 0),
                                file_info.get('type', 'application/octet-stream'),
                                'schedule_memo',
                                schedule_id,
                                owner_id
                            ))
                    
                    migrated_schedules += 1
                    print(f"  ✅ 스케줄 {schedule_id}: {len(files_data)}개 파일 마이그레이션 완료")
                    
            except json.JSONDecodeError:
                print(f"  ⚠️  스케줄 {schedule_id}: JSON 파싱 실패")
            except Exception as e:
                print(f"  ❌ 스케줄 {schedule_id}: 마이그레이션 실패 - {e}")
        
        # 2. 퀵메모의 첨부파일 정보 마이그레이션
        print("📝 퀵메모 첨부파일 마이그레이션...")
        
        # extra 필드에 JSON 데이터가 있는 퀵메모 조회
        cursor.execute("""
            SELECT id, extra, author_id 
            FROM quickmemos 
            WHERE extra IS NOT NULL 
            AND extra != '' 
            AND extra != 'null'
        """)
        
        quickmemo_files = cursor.fetchall()
        migrated_quickmemos = 0
        
        for quickmemo_id, extra, author_id in quickmemo_files:
            try:
                # JSON 파싱
                files_data = json.loads(extra)
                if isinstance(files_data, list) and files_data:
                    for file_info in files_data:
                        if isinstance(file_info, dict) and 'filename' in file_info:
                            cursor.execute("""
                                INSERT INTO memo_attachments 
                                (filename, file_path, file_size, mime_type, attachment_type, reference_id, uploader_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                file_info.get('filename', ''),
                                file_info.get('filepath', ''),
                                file_info.get('filesize', 0),
                                file_info.get('type', 'application/octet-stream'),
                                'quickmemo',
                                quickmemo_id,
                                author_id
                            ))
                    
                    migrated_quickmemos += 1
                    print(f"  ✅ 퀵메모 {quickmemo_id}: {len(files_data)}개 파일 마이그레이션 완료")
                    
            except json.JSONDecodeError:
                print(f"  ⚠️  퀵메모 {quickmemo_id}: JSON 파싱 실패")
            except Exception as e:
                print(f"  ❌ 퀵메모 {quickmemo_id}: 마이그레이션 실패 - {e}")
        
        conn.commit()
        print(f"🎉 마이그레이션 완료!")
        print(f"  - 스케줄: {migrated_schedules}개")
        print(f"  - 퀵메모: {migrated_quickmemos}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def cleanup_old_fields(db_path):
    """기존 JSON 필드들을 정리합니다 (선택사항)."""
    
    print("🧹 기존 JSON 필드 정리 중...")
    
    response = input("기존 memo_extra와 extra 필드의 JSON 데이터를 삭제하시겠습니까? (y/N): ")
    if response.lower() != 'y':
        print("ℹ️  기존 필드 정리 건너뜀")
        return True
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 스케줄의 memo_extra 필드 정리
        cursor.execute("""
            UPDATE schedules 
            SET memo_extra = NULL 
            WHERE memo_extra IS NOT NULL 
            AND memo_extra != ''
        """)
        
        # 퀵메모의 extra 필드 정리
        cursor.execute("""
            UPDATE quickmemos 
            SET extra = NULL 
            WHERE extra IS NOT NULL 
            AND extra != ''
        """)
        
        conn.commit()
        print("✅ 기존 JSON 필드 정리 완료")
        return True
        
    except Exception as e:
        print(f"❌ 필드 정리 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_migration(db_path):
    """마이그레이션 결과를 검증합니다."""
    
    print("🔍 마이그레이션 결과 검증 중...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 테이블 존재 확인
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='memo_attachments'
        """)
        
        if not cursor.fetchone():
            print("❌ memo_attachments 테이블이 존재하지 않습니다.")
            return False
        
        # 마이그레이션된 데이터 수 확인
        cursor.execute("SELECT COUNT(*) FROM memo_attachments")
        total_attachments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memo_attachments WHERE attachment_type = 'schedule_memo'")
        schedule_attachments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memo_attachments WHERE attachment_type = 'quickmemo'")
        quickmemo_attachments = cursor.fetchone()[0]
        
        print(f"📊 마이그레이션 결과:")
        print(f"  - 총 첨부파일: {total_attachments}개")
        print(f"  - 스케줄 메모: {schedule_attachments}개")
        print(f"  - 퀵메모: {quickmemo_attachments}개")
        
        # 샘플 데이터 확인
        if total_attachments > 0:
            cursor.execute("""
                SELECT filename, attachment_type, reference_id 
                FROM memo_attachments 
                LIMIT 5
            """)
            
            sample_data = cursor.fetchall()
            print(f"📋 샘플 데이터:")
            for filename, attachment_type, reference_id in sample_data:
                print(f"  - {filename} ({attachment_type}, ID: {reference_id})")
        
        return True
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")
        return False
    finally:
        conn.close()

def main():
    """메인 마이그레이션 함수"""
    
    print("🚀 메모 첨부파일 테이블 마이그레이션 시작")
    print("=" * 50)
    
    # 데이터베이스 파일 경로 확인
    db_path = "sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        print("현재 디렉토리의 .db 파일을 확인해주세요.")
        return False
    
    print(f"📁 데이터베이스: {db_path}")
    
    try:
        # 1. 테이블 생성
        if not create_memo_attachments_table(db_path):
            return False
        
        # 2. 기존 데이터 마이그레이션
        if not migrate_existing_data(db_path):
            return False
        
        # 3. 기존 필드 정리 (선택사항)
        cleanup_old_fields(db_path)
        
        # 4. 마이그레이션 결과 검증
        if not verify_migration(db_path):
            return False
        
        print("\n🎉 마이그레이션이 성공적으로 완료되었습니다!")
        print("\n다음 단계:")
        print("1. 서버를 재시작하여 새로운 테이블 구조를 적용하세요")
        print("2. 파일 업로드 디렉토리를 생성하세요: python create_upload_dirs.py")
        
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
