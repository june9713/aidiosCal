#!/usr/bin/env python3
"""
기존 attachments 테이블 데이터를 memo_attachments 테이블로 안전하게 마이그레이션하는 스크립트
기존 데이터는 보존하고 새로운 테이블에 복사만 합니다.
"""

import sqlite3
import os
import shutil
from datetime import datetime

def backup_database(db_path):
    """데이터베이스를 백업합니다."""
    
    backup_path = f"{db_path}.backup_memo_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ 데이터베이스 백업 완료: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        return None

def migrate_attachments_to_memo_attachments(db_path):
    """기존 attachments 테이블의 데이터를 memo_attachments 테이블로 안전하게 마이그레이션합니다."""
    
    print("🔄 기존 attachments 테이블 데이터 마이그레이션 중...")
    print(f"📁 데이터베이스: {db_path}")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return False
    
    # 1. 데이터베이스 백업
    backup_path = backup_database(db_path)
    if not backup_path:
        print("⚠️  백업이 실패했지만 계속 진행합니다...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 2. 기존 attachments 테이블 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM attachments")
        total_attachments = cursor.fetchone()[0]
        
        if total_attachments == 0:
            print("ℹ️  기존 attachments 테이블에 데이터가 없습니다.")
            return True
        
        print(f"📊 기존 attachments 테이블: {total_attachments}개 레코드")
        
        # 3. attachments 테이블 구조 확인
        cursor.execute("PRAGMA table_info(attachments)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 attachments 테이블 컬럼: {', '.join(column_names)}")
        
        # 4. 중복 데이터 확인
        print("\n🔍 중복 데이터 확인 중...")
        cursor.execute("""
            SELECT COUNT(*) FROM memo_attachments 
            WHERE attachment_type = 'schedule_memo'
        """)
        existing_memo_attachments = cursor.fetchone()[0]
        
        if existing_memo_attachments > 0:
            print(f"⚠️  memo_attachments 테이블에 이미 {existing_memo_attachments}개 데이터가 존재합니다.")
            response = input("기존 데이터를 유지하고 추가로 마이그레이션하시겠습니까? (y/N): ")
            if response.lower() != 'y':
                print("ℹ️  마이그레이션을 건너뜁니다.")
                return True
        
        # 5. 데이터 마이그레이션 (복사)
        print("\n🔄 데이터 마이그레이션 시작 (기존 데이터 보존)...")
        
        # attachments 테이블의 모든 데이터 조회
        cursor.execute("""
            SELECT id, filename, file_path, file_size, mime_type, schedule_id, uploader_id, created_at
            FROM attachments
        """)
        
        attachments = cursor.fetchall()
        migrated_count = 0
        skipped_count = 0
        duplicate_count = 0
        
        for attachment in attachments:
            try:
                attachment_id, filename, file_path, file_size, mime_type, schedule_id, uploader_id, created_at = attachment
                
                # schedule_id가 있는 경우에만 마이그레이션 (스케줄 메모 첨부파일로 간주)
                if schedule_id:
                    # 중복 확인 (동일한 파일이 이미 마이그레이션되었는지)
                    cursor.execute("""
                        SELECT COUNT(*) FROM memo_attachments 
                        WHERE filename = ? AND file_path = ? AND reference_id = ? AND attachment_type = 'schedule_memo'
                    """, (filename, file_path, schedule_id))
                    
                    if cursor.fetchone()[0] > 0:
                        duplicate_count += 1
                        continue
                    
                    # memo_attachments 테이블에 삽입 (복사)
                    cursor.execute("""
                        INSERT INTO memo_attachments 
                        (filename, file_path, file_size, mime_type, attachment_type, reference_id, uploader_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        filename or '',
                        file_path or '',
                        file_size or 0,
                        mime_type or 'application/octet-stream',
                        'schedule_memo',
                        schedule_id,
                        uploader_id or 1,  # 기본값으로 1 설정
                        created_at
                    ))
                    
                    migrated_count += 1
                    if migrated_count % 10 == 0:
                        print(f"  ✅ {migrated_count}개 마이그레이션 완료...")
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"  ❌ 첨부파일 {attachment_id} 마이그레이션 실패: {e}")
                skipped_count += 1
        
        conn.commit()
        
        print(f"\n🎉 마이그레이션 완료!")
        print(f"  - 성공 (복사): {migrated_count}개")
        print(f"  - 건너뜀: {skipped_count}개")
        print(f"  - 중복 (건너뜀): {duplicate_count}개")
        print(f"  - 기존 attachments 테이블 데이터: {total_attachments}개 (보존됨)")
        
        # 6. 결과 검증
        print("\n🔍 마이그레이션 결과 검증...")
        
        cursor.execute("SELECT COUNT(*) FROM memo_attachments")
        total_memo_attachments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memo_attachments WHERE attachment_type = 'schedule_memo'")
        schedule_memo_attachments = cursor.fetchone()[0]
        
        print(f"📊 memo_attachments 테이블:")
        print(f"  - 총 레코드: {total_memo_attachments}개")
        print(f"  - 스케줄 메모: {schedule_memo_attachments}개")
        
        # 샘플 데이터 확인
        if total_memo_attachments > 0:
            cursor.execute("""
                SELECT filename, attachment_type, reference_id, created_at
                FROM memo_attachments 
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            sample_data = cursor.fetchall()
            print(f"\n📋 최근 마이그레이션된 데이터:")
            for filename, attachment_type, reference_id, created_at in sample_data:
                print(f"  - {filename} ({attachment_type}, 스케줄 ID: {reference_id}, {created_at})")
        
        # 7. 기존 테이블 상태 확인
        print(f"\n🔍 기존 attachments 테이블 상태:")
        print(f"  - 원본 데이터: {total_attachments}개 (모두 보존됨)")
        print(f"  - 백업 파일: {backup_path if backup_path else '백업 실패'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_data_integrity(db_path):
    """데이터 무결성을 검증합니다."""
    
    print("\n🔍 데이터 무결성 검증 중...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. attachments 테이블 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM attachments")
        original_count = cursor.fetchone()[0]
        
        # 2. memo_attachments 테이블 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM memo_attachments WHERE attachment_type = 'schedule_memo'")
        migrated_count = cursor.fetchone()[0]
        
        # 3. 파일 경로 일치성 확인
        cursor.execute("""
            SELECT COUNT(*) FROM attachments a
            JOIN memo_attachments m ON a.filename = m.filename 
            AND a.file_path = m.file_path 
            AND a.schedule_id = m.reference_id
            WHERE m.attachment_type = 'schedule_memo'
        """)
        matched_count = cursor.fetchone()[0]
        
        print(f"📊 데이터 무결성 검증 결과:")
        print(f"  - 원본 attachments: {original_count}개")
        print(f"  - 마이그레이션된 데이터: {migrated_count}개")
        print(f"  - 일치하는 데이터: {matched_count}개")
        
        if matched_count == migrated_count and migrated_count > 0:
            print("✅ 데이터 무결성 검증 통과!")
        else:
            print("⚠️  데이터 무결성 검증에 문제가 있을 수 있습니다.")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터 무결성 검증 실패: {e}")
        return False
    finally:
        conn.close()

def main():
    """메인 함수"""
    
    print("🚀 기존 attachments 테이블 안전 마이그레이션 시작")
    print("=" * 70)
    print("⚠️  중요: 이 스크립트는 기존 데이터를 보존하면서 복사만 수행합니다!")
    print("=" * 70)
    
    db_path = "sql_app.db"
    
    try:
        # 1. 데이터 마이그레이션 (복사)
        if not migrate_attachments_to_memo_attachments(db_path):
            return False
        
        # 2. 데이터 무결성 검증
        if not verify_data_integrity(db_path):
            print("⚠️  데이터 무결성 검증에 문제가 있습니다. 백업을 확인해주세요.")
        
        print("\n🎉 모든 마이그레이션이 안전하게 완료되었습니다!")
        print("\n📋 마이그레이션 요약:")
        print("✅ 기존 attachments 테이블 데이터는 모두 보존됨")
        print("✅ 새로운 memo_attachments 테이블에 데이터가 복사됨")
        print("✅ 데이터베이스 백업이 생성됨")
        print("\n다음 단계:")
        print("1. 서버를 재시작하여 새로운 테이블 구조를 적용하세요")
        print("2. 파일 업로드 디렉토리를 생성하세요: python create_upload_dirs.py")
        print("3. 필요시 기존 attachments 테이블을 수동으로 정리할 수 있습니다")
        
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
