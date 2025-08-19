from enum import Enum

class PriorityLevel(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TURTLE = "turtle"

class AlarmType(str, Enum):
    SCHEDULE_DUE = "schedule_due"
    MEMO = "memo"
    SHARE = "share"
    COMPLETION_REQUEST = "completion_request" 