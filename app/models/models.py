from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Enum
from sqlalchemy.orm import relationship, backref
from datetime import datetime
import enum
from app.core.database import Base

class PriorityLevel(enum.Enum):
    URGENT = "긴급"
    HIGH = "급함"
    MEDIUM = "곧임박"
    LOW = "일반"
    TURTLE = "거북이"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    schedules = relationship("Schedule", back_populates="owner", foreign_keys="Schedule.owner_id")
    memo_schedules = relationship("Schedule", back_populates="memo_author", foreign_keys="Schedule.memo_author_id")
    shared_schedules = relationship("ScheduleShare", back_populates="shared_with")

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    date = Column(DateTime, default=datetime.now)
    due_time = Column(DateTime)
    alarm_time = Column(DateTime)
    priority = Column(Enum(PriorityLevel))
    is_completed = Column(Boolean, default=False)
    individual = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    memo = Column(Text)
    memo_author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    memo_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    project_name = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("schedules.id"), nullable=True)
    parent_order = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, default=False)
    
    owner = relationship("User", back_populates="schedules", foreign_keys=[owner_id])
    memo_author = relationship("User", foreign_keys=[memo_author_id])
    shares = relationship("ScheduleShare", back_populates="schedule")
    attachments = relationship("Attachment", back_populates="schedule")
    parent = relationship("Schedule", remote_side=[id], backref=backref("children", lazy="select"))

class ScheduleShare(Base):
    __tablename__ = "schedule_shares"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    shared_with_id = Column(Integer, ForeignKey("users.id"))
    memo = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    can_edit = Column(Boolean, default=True)
    can_delete = Column(Boolean, default=True)
    can_complete = Column(Boolean, default=True)
    can_share = Column(Boolean, default=True)
    role = Column(String, default="collaborator")
    added_at = Column(DateTime, default=datetime.now)
    
    schedule = relationship("Schedule", back_populates="shares")
    shared_with = relationship("User", back_populates="shared_schedules")

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    mime_type = Column(String)
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    uploader_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)

    schedule = relationship("Schedule", back_populates="attachments")
    uploader = relationship("User", backref="uploads")

class AlarmType(enum.Enum):
    SCHEDULE_DUE = "schedule_due"
    MEMO = "memo"
    SHARE = "share"
    COMPLETION_REQUEST = "completion_request"

class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    type = Column(Enum(AlarmType))
    message = Column(Text)
    is_activated = Column(Boolean, default=False)
    is_acked = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    activated_at = Column(DateTime, nullable=True)
    acked_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="alarms")
    schedule = relationship("Schedule", backref="alarms")

class QuickMemo(Base):
    __tablename__ = "quickmemos"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    is_completed = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    author = relationship("User", backref="quickmemos") 