from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
from pathlib import Path
from pydantic import BaseModel
from ..routers.auth import get_current_user

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str

@router.get("/")
async def get_projects():
    """프로젝트 목록을 반환합니다"""
    try:
        # JSON 파일 경로
        json_path = Path("static/json/projects.json")
        
        # JSON 파일 읽기
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return data["projects"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def add_project(project: ProjectCreate, current_user = Depends(get_current_user)):
    """새로운 프로젝트를 추가합니다"""
    try:
        # JSON 파일 경로
        json_path = Path("static/json/projects.json")
        
        # JSON 파일 읽기
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 이미 존재하는 프로젝트인지 확인
        existing_projects = [p["name"] for p in data["projects"]]
        if project.name in existing_projects:
            raise HTTPException(status_code=400, detail="이미 존재하는 프로젝트입니다")
        
        # 새로운 프로젝트 추가
        data["projects"].append({"name": project.name})
        
        # JSON 파일에 저장
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        return {"message": "프로젝트가 추가되었습니다", "project": {"name": project.name}}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 