from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.routing import APIRoute
from fastapi.responses import Response, JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Callable, Optional
from datetime import timedelta
from pydantic import ValidationError
import json
from app.core.database import get_db, SessionLocal
from app.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_active_user,
    get_current_user,
    decode_access_token
)
from app.models.models import User
from app.schemas.schemas import UserCreate, User as UserSchema, Token
#from app.core.logger import setup_logger, log_function_call
import traceback

# 로거 설정
#logger = setup_logger(__name__)

# 커스텀 라우트 클래스를 사용하는 라우터 생성
router = APIRouter()

@router.post("/register", response_model=UserSchema)
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    try:
        # 요청 데이터 로깅
        print("=== Register Request Validation Start ===")
        print(f"Request body: {user.dict()}")
        
        # 중복 사용자 확인
        db_user = db.query(User).filter(User.username == user.username).first()
        if db_user:
            print(f"Username already registered: {user.username}")
            raise HTTPException(
                status_code=400,
                detail="Username already registered"
            )
        
        # 새 사용자 생성
        db_user = User(
            is_active=True,
            username=user.username,
            name=user.name,
            hashed_password=user.password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        print(f"User registered successfully: {user.username}")
        
        return UserSchema(
            id=int(db_user.id),
            username=db_user.username,
            name=db_user.name,
            is_active=db_user.is_active
        )
        
    except ValidationError as e:
        print(f"[register_user] Validation Error: {str(e)}")
        print(f"[register_user] Validation Error Details: {e.errors()}")
        # db가 Session 객체인지 확인 후 rollback
        if hasattr(db, 'rollback'):
            db.rollback()
        raise HTTPException(
            status_code=422,
            detail=e.errors()
        )
    except HTTPException:
        # HTTPException은 다시 발생시키되, rollback만 수행
        if hasattr(db, 'rollback'):
            db.rollback()
        raise
    except Exception as e:
        print(f"Registration failed: {str(e)}")#, exc_info=True)
        if hasattr(db, 'rollback'):
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )

@router.get("/users/", response_model=List[UserSchema])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        print(f"Fetching users list (skip: {skip}, limit: {limit}, search: {search})")
        
        query = db.query(User).filter(User.is_active == True)
        
        # 검색어가 있는 경우 필터링
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_term),
                    User.name.ilike(search_term)
                )
            )
        
        users = query.offset(skip).limit(limit).all()
        print(f"Found {len(users)} users")
        return users
    except Exception as e:
        print(f"Failed to fetch users: {str(e)}")#, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        print(f"Login attempt for username: {form_data.username}")
        
        # 사용자 확인
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user:
            print(f"Login failed: User not found - {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 비밀번호 확인
        if (form_data.password != user.hashed_password):
            print(f"Login failed: Invalid password for user - {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 토큰 생성
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        print(f"Login successful for user: {form_data.username}")
        
        # JSONResponse로 응답 생성하여 쿠키 설정
        response = JSONResponse(content={
            "access_token": access_token, 
            "token_type": "bearer"
        })
        
        # HttpOnly 쿠키 설정 (30일 유지)
        response.set_cookie(
            key="session_token",
            value=access_token,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 초 단위로 변환
            httponly=True,
            secure=False,  # HTTPS 환경에서는 True로 설정
            samesite="lax"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login failed: {str(e)}")#, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create access token: {str(e)}"
        )

@router.post("/token/refresh", response_model=Token)
async def refresh_access_token(
    current_user: User = Depends(get_current_user)
):
    try:
        print(f"Token refresh attempt for user: {current_user.username}")
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": current_user.username}, expires_delta=access_token_expires
        )
        
        print(f"Token refreshed successfully for user: {current_user.username}")
        
        # JSONResponse로 응답 생성하여 쿠키 업데이트
        response = JSONResponse(content={
            "access_token": access_token, 
            "token_type": "bearer"
        })
        
        # HttpOnly 쿠키 업데이트
        response.set_cookie(
            key="session_token",
            value=access_token,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 초 단위로 변환
            httponly=True,
            secure=False,  # HTTPS 환경에서는 True로 설정
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        print(f"Token refresh failed: {str(e)}")#, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )

@router.post("/logout")
async def logout():
    """로그아웃 처리 - 쿠키 삭제"""
    response = JSONResponse(content={"message": "Logout successful"})
    response.delete_cookie(key="session_token")
    return response

@router.get("/users/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    print(f"Fetching user profile for: {current_user.username}")
    return UserSchema(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        is_active=current_user.is_active
    )

@router.get("/check-session")
async def check_session(request: Request, db: Session = Depends(get_db)):
    """쿠키 기반 세션 체크"""
    try:
        # 쿠키에서 토큰 가져오기
        session_token = request.cookies.get("session_token")
        
        if not session_token:
            return {"authenticated": False, "message": "No session cookie found"}
        
        # 토큰 검증
        try:
            username = decode_access_token(session_token)
            
            # 사용자 정보 조회
            user = db.query(User).filter(User.username == username).first()
            if not user or not user.is_active:
                return {"authenticated": False, "message": "User not found or inactive"}
            
            return {
                "authenticated": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "is_active": user.is_active
                },
                "token": session_token
            }
            
        except Exception as token_error:
            print(f"Token validation failed: {str(token_error)}")
            return {"authenticated": False, "message": "Invalid token"}
            
    except Exception as e:
        print(f"Session check failed: {str(e)}")
        return {"authenticated": False, "message": "Session check failed"}