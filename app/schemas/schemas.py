from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional, List, ForwardRef
from datetime import datetime
from app.models.models import PriorityLevel
from .enums import AlarmType

class UserBase(BaseModel):
    username: str
    name: str

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "user"

class User(UserBase):
    id: int
    is_active: bool
    role: Optional[str] = None

    class Config:
        from_attributes = True

class AttachmentBase(BaseModel):
    filename: str
    file_size: int
    mime_type: str

class AttachmentCreate(AttachmentBase):
    schedule_id: int

class Attachment(AttachmentBase):
    id: int
    file_path: str
    schedule_id: int
    uploader_id: int
    created_at: datetime
    uploader: Optional[User] = None
    schedule_title: Optional[str] = None
    project_name: Optional[str] = None

    class Config:
        from_attributes = True

class ScheduleBase(BaseModel):
    title: str
    content: Optional[str] = None
    date: datetime
    due_time: Optional[datetime] = None
    alarm_time: Optional[datetime] = None
    priority: PriorityLevel
    individual: Optional[bool] = False
    project_name: Optional[str] = None
    parent_id: Optional[int] = None
    parent_order: Optional[int] = 0

class ScheduleCreate(ScheduleBase):
    collaborators: Optional[List[int]] = []  # 공동작업자 ID 리스트 추가

class ScheduleShareBase(BaseModel):
    schedule_id: int
    shared_with_id: int
    memo: Optional[str] = None

class ScheduleShareCreate(ScheduleShareBase):
    pass

class ScheduleShare(ScheduleShareBase):
    id: int
    created_at: datetime
    shared_with: Optional[User] = None

    class Config:
        from_attributes = True

class Schedule(ScheduleBase):
    id: int
    owner_id: int
    memo: Optional[str] = None
    memo_author_id: Optional[int] = None
    memo_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_completed: bool = False
    individual: bool = False
    owner: User
    memo_author: Optional[User] = None
    shares: List[ScheduleShare] = []
    attachments: List[Attachment] = []
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True

    @computed_field
    @property
    def is_shared(self) -> bool:
        return len(self.shares) > 0 if self.shares else False

class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[datetime] = None
    due_time: Optional[datetime] = None
    alarm_time: Optional[datetime] = None
    priority: Optional[PriorityLevel] = None
    individual: Optional[bool] = None
    memo: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class AlarmBase(BaseModel):
    type: AlarmType
    message: str
    schedule_id: int

class AlarmCreate(AlarmBase):
    pass

class Alarm(AlarmBase):
    id: int
    user_id: int
    is_read: bool
    is_acked: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    acked_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class QuickMemoBase(BaseModel):
    content: str

class QuickMemoCreate(QuickMemoBase):
    pass

class QuickMemo(QuickMemoBase):
    id: int
    author_id: int
    created_at: datetime
    is_completed: bool = False
    is_deleted: bool = False
    author: Optional[User] = None

    class Config:
        from_attributes = True

class QuickMemoUpdate(BaseModel):
    content: Optional[str] = None
    is_completed: Optional[bool] = None