#!/usr/bin/env python3
"""
파일 업로드 디렉토리 생성 스크립트
기존 static/uploads 폴더를 활용하여 메모와 퀵메모 첨부파일을 저장할 디렉토리를 생성합니다.
"""

import os

def create_upload_directories():
    """기존 static/uploads 폴더에 필요한 하위 디렉토리를 생성합니다."""
    
    # 기존 static/uploads 폴더 활용
    base_dirs = [
        "static/uploads",
        "static/uploads/memo_files",
        "static/uploads/quicknote_files"
    ]
    
    for dir_path in base_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ 디렉토리 생성됨: {dir_path}")
        else:
            print(f"ℹ️  디렉토리 이미 존재: {dir_path}")
    
    # .gitkeep 파일 생성 (빈 디렉토리도 git에 포함되도록)
    for dir_path in base_dirs:
        gitkeep_file = os.path.join(dir_path, ".gitkeep")
        if not os.path.exists(gitkeep_file):
            with open(gitkeep_file, 'w') as f:
                pass
            print(f"📁 .gitkeep 파일 생성: {gitkeep_file}")
    
    # 기존 파일 확인
    existing_files = []
    for root, dirs, files in os.walk("static/uploads"):
        for file in files:
            if file != ".gitkeep":
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                existing_files.append((file_path, file_size))
    
    if existing_files:
        print(f"\n📋 기존 업로드된 파일들:")
        for file_path, file_size in existing_files:
            size_kb = file_size / 1024
            print(f"  - {file_path} ({size_kb:.1f} KB)")
    else:
        print(f"\n📋 기존 업로드된 파일: 없음")

if __name__ == "__main__":
    print("🚀 기존 static/uploads 폴더 활용하여 디렉토리 생성 시작...")
    create_upload_directories()
    print("🎉 모든 디렉토리 생성 완료!")
    print("\n📁 폴더 구조:")
    print("  static/uploads/")
    print("  ├── memo_files/          # 스케줄 메모 첨부파일")
    print("  ├── quicknote_files/     # 퀵메모 첨부파일")
    print("  └── [기존 파일들]        # 기존 업로드된 파일들")
