from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm import Session
from app.models.models import Schedule, Alarm, AlarmType, User
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

def format_alarm_message(schedule, alarm_time):
    """알람 메시지를 포맷팅합니다."""
    project_name = schedule.project_name or "프로젝트 미지정"
    formatted_time = alarm_time.strftime("%Y-%m-%d %H:%M")
    return f"{project_name}:{schedule.title}:{formatted_time}"

def create_alarms_for_schedule(db: Session, schedule: Schedule, alarm_time: datetime, current_time: datetime):
    """일정에 대한 알람을 생성합니다. 개인일정은 본인에게만, 일반일정은 모든 유저에게."""
    if schedule.individual:
        # 개인일정: 본인에게만 알람 생성
        new_alarm = Alarm(
            user_id=schedule.owner_id,
            schedule_id=schedule.id,
            type=AlarmType.SCHEDULE_DUE,
            message=format_alarm_message(schedule, alarm_time),
            is_activated=True,
            activated_at=current_time
        )
        db.add(new_alarm)
        logger.info(f"Created individual alarm for schedule: {schedule.title} (owner: {schedule.owner_id})")
    else:
        # 일반일정: 모든 유저에게 알람 생성
        all_users = db.query(User).all()
        for user in all_users:
            new_alarm = Alarm(
                user_id=user.id,
                schedule_id=schedule.id,
                type=AlarmType.SCHEDULE_DUE,
                message=format_alarm_message(schedule, alarm_time),
                is_activated=True,
                activated_at=current_time
            )
            db.add(new_alarm)
        logger.info(f"Created public alarms for schedule: {schedule.title} (sent to {len(all_users)} users)")

async def check_schedules():
    """1분마다 모든 유저의 알람을 체크하고 상태를 업데이트합니다."""
    while True:
        try:
            db = SessionLocal()
            current_time = datetime.now()
            
            # 1. 알람 시간이 되었지만 아직 활성화되지 않은 알람 체크
            schedules = db.query(Schedule).filter(
                Schedule.alarm_time.isnot(None),
                Schedule.alarm_time <= current_time,
                Schedule.is_completed == False,
                Schedule.is_deleted == False
            ).all()
            #print("schedules", schedules)

            for schedule in schedules:
                # 이미 활성화된 알람이 있는지 확인 (개인일정의 경우 소유자, 일반일정의 경우 아무나)
                if schedule.individual:
                    existing_alarm = db.query(Alarm).filter(
                        Alarm.schedule_id == schedule.id,
                        Alarm.user_id == schedule.owner_id,
                        Alarm.type == AlarmType.SCHEDULE_DUE,
                        Alarm.is_deleted == False,
                        Alarm.is_acked == False
                    ).first()
                else:
                    existing_alarm = db.query(Alarm).filter(
                        Alarm.schedule_id == schedule.id,
                        Alarm.type == AlarmType.SCHEDULE_DUE,
                        Alarm.is_deleted == False,
                        Alarm.is_acked == False
                    ).first()

                if not existing_alarm:
                    # 새로운 알람 생성
                    create_alarms_for_schedule(db, schedule, schedule.alarm_time, current_time)
                elif not existing_alarm.is_activated and schedule.alarm_time <= current_time:
                    # 기존 알람이 있지만 활성화되지 않은 경우
                    existing_alarm.is_activated = True
                    existing_alarm.activated_at = current_time
                    existing_alarm.message = format_alarm_message(schedule, schedule.alarm_time)
                    logger.info(f"Activated existing alarm for schedule: {schedule.title}")

            # 2. 마감 시간이 지난 일정에 대한 알람 처리
            overdue_schedules = db.query(Schedule).filter(
                Schedule.due_time.isnot(None),
                Schedule.due_time <= current_time,
                Schedule.is_completed == False,
                Schedule.is_deleted == False
            ).all()

            for schedule in overdue_schedules:
                # 마감 시간 초과 알람이 있는지 확인
                existing_overdue_alarm = db.query(Alarm).filter(
                    Alarm.schedule_id == schedule.id,
                    Alarm.type == AlarmType.SCHEDULE_DUE,
                    Alarm.message.like("%종료%"),
                    Alarm.is_deleted == False
                ).first()

                if not existing_overdue_alarm:
                    # 마감 시간 초과 알람 생성은 주석 처리됨
                    pass

            db.commit()
            logger.info("Completed alarm check cycle")
            
        except Exception as e:
            logger.error(f"Error in alarm checker: {str(e)}")
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()

        # 1분마다 체크
        await asyncio.sleep(60)

async def start_alarm_checker():
    """알람 체커를 시작합니다."""
    logger.info("Starting alarm checker...")
    await check_schedules() 