import pytest
from sqlalchemy.orm import Session
from app.models.models import Schedule, User, PriorityLevel
from datetime import datetime, timedelta
from app.core.database import Base, engine

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db):
    user = User(
        username="testuser",
        name="Test User",
        hashed_password="hashed_password"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def parent_schedule(db, test_user):
    schedule = Schedule(
        title="Parent Schedule",
        content="Parent content",
        date=datetime.now(),
        priority=PriorityLevel.MEDIUM,
        owner_id=test_user.id
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule

def test_create_child_schedule(db, test_user, parent_schedule):
    # 첫 번째 자식 스케줄 생성
    child1 = Schedule(
        title="Child Schedule 1",
        content="Child content 1",
        date=datetime.now(),
        priority=PriorityLevel.MEDIUM,
        owner_id=test_user.id,
        parent_id=parent_schedule.id,
        child_order=1
    )
    db.add(child1)
    db.commit()
    db.refresh(child1)

    # 두 번째 자식 스케줄 생성
    child2 = Schedule(
        title="Child Schedule 2",
        content="Child content 2",
        date=datetime.now(),
        priority=PriorityLevel.MEDIUM,
        owner_id=test_user.id,
        parent_id=parent_schedule.id,
        child_order=2
    )
    db.add(child2)
    db.commit()
    db.refresh(child2)

    # 자식 스케줄 조회
    children = db.query(Schedule).filter(
        Schedule.parent_id == parent_schedule.id
    ).order_by(Schedule.child_order).all()

    assert len(children) == 2
    assert children[0].child_order == 1
    assert children[1].child_order == 2
    assert children[0].title == "Child Schedule 1"
    assert children[1].title == "Child Schedule 2"

def test_get_next_child_order(db, test_user, parent_schedule):
    # 기존 자식 스케줄 생성
    child1 = Schedule(
        title="Child Schedule 1",
        content="Child content 1",
        date=datetime.now(),
        priority=PriorityLevel.MEDIUM,
        owner_id=test_user.id,
        parent_id=parent_schedule.id,
        child_order=1
    )
    db.add(child1)
    db.commit()

    # 다음 자식 순서 조회
    next_order = db.query(Schedule).filter(
        Schedule.parent_id == parent_schedule.id
    ).count() + 1

    assert next_order == 2

def test_reorder_children(db, test_user, parent_schedule):
    # 여러 자식 스케줄 생성
    children = []
    for i in range(3):
        child = Schedule(
            title=f"Child Schedule {i+1}",
            content=f"Child content {i+1}",
            date=datetime.now(),
            priority=PriorityLevel.MEDIUM,
            owner_id=test_user.id,
            parent_id=parent_schedule.id,
            child_order=i+1
        )
        db.add(child)
        children.append(child)
    db.commit()

    # 자식 순서 변경 (두 번째 자식을 마지막으로 이동)
    children[1].child_order = 3
    db.commit()

    # 변경된 순서 확인
    reordered_children = db.query(Schedule).filter(
        Schedule.parent_id == parent_schedule.id
    ).order_by(Schedule.child_order).all()

    assert len(reordered_children) == 3
    assert reordered_children[0].child_order == 1
    assert reordered_children[1].child_order == 2
    assert reordered_children[2].child_order == 3
    assert reordered_children[2].title == "Child Schedule 2" 