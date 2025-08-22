from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pathlib import Path
from app.core.database import engine, Base, get_db
from app.routers import auth, schedules, alarms, attachments, projects, quickmemos
from app.routers.auth import get_current_user
from app.models.models import Alarm
from sqlalchemy.orm import Session
from datetime import datetime
#from app.core.logger import setup_logger, log_function_call
from app.models.models import Schedule, AlarmType
import uvicorn
import asyncio
from app.core.alarm_checker import start_alarm_checker
from contextlib import asynccontextmanager
from typing import Optional
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from app.core.auth import SECRET_KEY, ALGORITHM
from app.models.models import User
print("app start")

# 로거 설정
#logger = setup_logger(__name__)
import os
import datetime
import logging
import sys
import time

# 로그 포맷 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)




def is_running_in_vscode():
    """VSCode 터미널에서 실행중인지 확인"""
    return os.environ.get('TERM_PROGRAM') == 'vscode'

def get_terminal_type():
    """터미널 타입 반환"""
    term_program = os.environ.get('TERM_PROGRAM')
    
    if term_program == 'vscode':
        return 'VSCode'
    elif term_program == 'Apple_Terminal':
        return 'macOS Terminal'
    elif 'VSCODE_PID' in os.environ:
        return 'VSCode (indirect)'
    else:
        return 'Native Terminal'






logger = logging.getLogger(__name__)
# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    asyncio.create_task(start_alarm_checker())
    yield
    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(title="Schedule Management System", lifespan=lifespan)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path("static")
static_path.mkdir(exist_ok=True)

# entryScreen.html 동적 라우트 (static 마운트 전에 정의)
@app.get("/entryScreen/{screen_id}", response_class=HTMLResponse)
async def get_entry_screen_dynamic(screen_id: int):
    """화면별 독립적인 entryScreen.html 제공 (동적 라우트)"""
    logger.info(f"Requested entryScreen.html with screen_id: {screen_id}")
    try:
        with open("static/entryScreen.html", "r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"Successfully served entryScreen.html for screen_id: {screen_id}")
            return content
    except FileNotFoundError:
        logger.error(f"entryScreen.html not found for screen_id: {screen_id}")
        raise HTTPException(status_code=404, detail="entryScreen.html not found")

app.mount("/static", StaticFiles(directory="static"), name="static")

# 업로드된 파일들을 정적 파일로 서빙
uploads_path = Path("uploads")
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router, tags=["authentication"])
app.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
app.include_router(alarms.router, prefix="/alarms", tags=["alarms"])
app.include_router(attachments.router, prefix="/attachments", tags=["attachments"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(quickmemos.router, tags=["quickmemos"])


@app.get("/debug/routes")
async def debug_routes():
    """등록된 모든 라우트를 확인합니다."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append({
                'path': route.path,
                'methods': getattr(route, 'methods', [])
            })
    return routes

# 선택적 인증을 위한 HTTPBearer 스키마
security = HTTPBearer(auto_error=False)

async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    선택적 사용자 인증 - 토큰이 없거나 유효하지 않아도 None을 반환
    """
    # 먼저 쿠키에서 토큰 확인
    token = request.cookies.get("session_token")
    
    if not token:
        # Authorization 헤더에서 토큰 확인
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None
    except Exception:
        return None

@app.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    루트 라우트 - 세션 확인 후 적절한 페이지로 리디렉션
    1. 세션 없을 시 로그인 페이지
    2. 세션 있을 시 마지막 페이지로 이동 (없으면 entryScreen/0)
    """
    if not current_user:
        # 세션이 없으면 로그인 페이지 반환
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    else:
        # 세션이 있으면 마지막 페이지 확인 후 리디렉션하는 HTML 반환
        redirect_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>리디렉션 중...</title>
</head>
<body>
    <div style="text-align: center; margin-top: 50px;">
        <h2>페이지를 로딩 중입니다...</h2>
        <p>잠시만 기다려주세요.</p>
    </div>
    <script>
        // 로컬 스토리지에서 마지막 페이지 확인
        const lastPage = localStorage.getItem('lastPage');
        
        if (lastPage && lastPage !== '/') {{
            // 마지막 페이지가 있으면 해당 페이지로 이동
            window.location.href = lastPage;
        }} else {{
            // 마지막 페이지가 없으면 entryScreen/0으로 이동
            window.location.href = '/entryScreen/0';
        }}
    </script>
</body>
</html>
        """
        return redirect_html

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

# 알람 엔드포인트들 (기존 get_current_user 사용)
@app.get("/alarms")
async def get_alarms(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 알람 목록을 반환합니다"""
    alarms = db.query(Alarm).filter(
        Alarm.user_id == current_user.id,
        Alarm.is_deleted == False
    ).order_by(Alarm.created_at.desc()).all()
    #print(alarms)
    return [
        {
            "id": alarm.id,
            "type": alarm.type.value,
            "message": alarm.message,
            "is_acked": alarm.is_acked,
            "created_at": alarm.created_at.isoformat(),
            "schedule_id": alarm.schedule_id
        }
        for alarm in alarms
    ]

@app.post("/ack_alarms/{alarm_id}/ack")
async def acknowledge_alarm(
    alarm_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알람을 확인 처리합니다"""
    alarm = db.query(Alarm).filter(
        Alarm.id == alarm_id,
        Alarm.user_id == current_user.id
    ).first()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    alarm.is_acked = True
    alarm.acked_at = datetime.datetime.now()
    db.commit()
    
    return {"message": "Alarm acknowledged", "alarm_id": alarm_id}

@app.delete("/delete_alarms/{alarm_id}")
async def delete_alarm(
    alarm_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """개별 알람을 삭제합니다 (soft delete)"""
    alarm = db.query(Alarm).filter(
        Alarm.id == alarm_id,
        Alarm.user_id == current_user.id,
        Alarm.is_deleted == False
    ).first()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    # 실제 삭제 대신 is_deleted 플래그를 True로 설정
    alarm.is_deleted = True
    alarm.is_acked = True
    
    db.commit()
    
    return {"message": "Alarm deleted", "alarm_id": alarm_id}

@app.delete("/clear_alarms/clear")
async def clear_all_alarms(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """모든 알람을 삭제합니다 (soft delete)"""
    db.query(Alarm).filter(
        Alarm.user_id == current_user.id,
        Alarm.is_deleted == False
    ).update({"is_deleted": True})
    db.commit()
    
    return {"message": "All alarms cleared"}

@app.post("/schedules/{schedule_id}/request-completion")
async def request_completion(schedule_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """일정 완료 요청을 처리합니다"""
    # 일정 조회
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="스케쥴이 존재하지 않습니다")
    
    # 자신의 일정에 대한 완료 요청은 무시
    if schedule.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="자신의 스케쥴에는 완료요청을 할수 없습니다")
    
    # 이미 완료된 일정인 경우
    if schedule.is_completed:
        raise HTTPException(status_code=400, detail="스케쥴이 이미 완료되었습니다")
    
    # 완료 요청 알람 생성
    new_alarm = Alarm(
        user_id=schedule.owner_id,  # 일정 소유자에게 알림
        schedule_id=schedule_id,
        type=AlarmType.COMPLETION_REQUEST,
        message=f"{current_user.name}님이 일정 '{schedule.title}'의 완료를 요청했습니다."
    )
    
    db.add(new_alarm)
    db.commit()
    
    return {"message": "Completion request sent", "schedule_id": schedule_id}

@app.get("/gettimenow")
async def get_server_time():
    """서버의 로컬 시간을 반환합니다."""
    # 현재 시간에 9시간(32400초) 추가
    adjusted_timestamp = time.time() + (9 * 3600)
    adjusted_localtime = time.localtime(adjusted_timestamp)
    
    # JavaScript에서 받을 수 있도록 리스트 형태로 반환
    time_array = [
        adjusted_localtime.tm_year,   # [0] year
        adjusted_localtime.tm_mon,    # [1] month  
        adjusted_localtime.tm_mday,   # [2] day
        adjusted_localtime.tm_hour,   # [3] hour
        adjusted_localtime.tm_min,    # [4] minute
        adjusted_localtime.tm_sec     # [5] second
    ]
    
    return {"time": time_array}

if __name__ == "__main__":
    # 사용 예시
    in_vscode = is_running_in_vscode()
    if in_vscode:
        print("VSCode에서 실행 중입니다!")
    else:
        print("네이티브 터미널에서 실행 중입니다!")


    if in_vscode:
        uvicorn.run(app, host="0.0.0.0", port=8124, log_level="debug",access_log=True )
    else:
        uvicorn.run(app, host="0.0.0.0", port=8123, log_level="debug",access_log=True )