from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User
#from app.core.logger import setup_logger, log_function_call

# 로거 설정
#logger = setup_logger(__name__)

# JWT 설정
SECRET_KEY = "your-secret-key"  # 실제 운영 환경에서는 환경 변수로 관리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200  # 30일 (30 * 24 * 60 = 43,200분)

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

##@log_function_call(logger)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증
    
    Args:
        plain_password (str): 평문 비밀번호
        hashed_password (str): 해시된 비밀번호
    
    Returns:
        bool: 비밀번호 일치 여부
    """
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        print("debug" , "Password verification completed")
        return result
    except Exception as e:
        print("error" , f"Password verification failed: {str(e)}")#)#)#, exc_info=True)
        raise

#@log_function_call(logger)
def get_password_hash(password: str) -> str:
    """
    비밀번호 해싱
    
    Args:
        password (str): 평문 비밀번호
    
    Returns:
        str: 해시된 비밀번호
    """
    try:
        hashed = pwd_context.hash(password)
        print("debug" , "Password hashed successfully")
        return hashed
    except Exception as e:
        print("error" , f"Password hashing failed: {str(e)}")#)#, exc_info=True)
        raise

#@log_function_call(logger)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰 생성
    
    Args:
        data (dict): 토큰에 포함할 데이터
        expires_delta (Optional[timedelta]): 토큰 만료 시간
    
    Returns:
        str: 생성된 JWT 토큰
    """
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        print("debug" , "Access token created successfully")
        return encoded_jwt
    except Exception as e:
        print("error" , f"Token creation failed: {str(e)}")#)#, exc_info=True)
        raise

#@log_function_call(logger)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자 정보 조회
    
    Args:
        token (str): JWT 토큰
        db (Session): 데이터베이스 세션
    
    Returns:
        User: 사용자 정보
    
    Raises:
        HTTPException: 인증 실패 시
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        #print("debug" , "Decoding JWT token")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            print("warning" , "Token payload missing 'sub' field")
            raise credentials_exception
    except JWTError as e:
        print("error" , f"JWT decode error: {str(e)}")#)#)#, exc_info=True)
        raise credentials_exception

    try:
        #print("debug" , f"Fetching user from database: {username}")
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            print("warning" , f"User not found: {username}")
            raise credentials_exception
        return user
    except Exception as e:
        print("error" , f"Database error while fetching user: {str(e)}")#)#)#, exc_info=True)
        raise credentials_exception

#@log_function_call(logger)
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    현재 활성화된 사용자 정보 조회
    
    Args:
        current_user (User): 현재 인증된 사용자
    
    Returns:
        User: 활성화된 사용자 정보
    
    Raises:
        HTTPException: 사용자가 비활성화 상태일 경우
    """
    if not current_user.is_active:
        print("warning" , f"Inactive user attempted access: {current_user.username}")
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

#@log_function_call(logger)
def decode_access_token(token: str) -> str:
    """
    JWT 토큰을 디코딩하여 사용자명 반환
    
    Args:
        token (str): JWT 토큰
    
    Returns:
        str: 사용자명
    
    Raises:
        Exception: 토큰 검증 실패 시
    """
    try:
        #print("debug", "Decoding JWT token for username")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise Exception("Token payload missing 'sub' field")
        print("debug", f"Token decoded successfully for user: {username}")
        return username
    except JWTError as e:
        print("error", f"JWT decode error: {str(e)}")
        raise Exception(f"Invalid token: {str(e)}")
    except Exception as e:
        print("error", f"Token decode failed: {str(e)}")
        raise 