from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
#from app.core.logger import setup_logger, log_function_call

# 로거 설정
#logger = setup_logger(__name__)

# 데이터베이스 URL 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///sql_app.db"

# 엔진 생성
try:
    print("info"  , "Creating database engine")
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    print("debug"  , "Database engine created successfully")
except Exception as e:
    print("error"  , f"Failed to create database engine: {str(e)}")#, exc_info=True)
    raise

# 세션 생성
try:
    print("info"  , "Creating database session")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("debug"  , "Database session created successfully")
except Exception as e:
    print("error"  , f"Failed to create database session: {str(e)}")#, exc_info=True)
    raise

# Base 클래스 생성
Base = declarative_base()

# 데이터베이스 테이블 생성
def init_db():
    """
    데이터베이스 테이블 초기화
    """
    try:
        print("info"  , "Creating database tables")
        Base.metadata.create_all(bind=engine)
        print("debug"  , "Database tables created successfully")
    except Exception as e:
        print("error"  , f"Failed to create database tables: {str(e)}")#, exc_info=True)
        raise

# 애플리케이션 시작 시 테이블 생성
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()