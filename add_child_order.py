from sqlalchemy import create_engine, Column, Integer, text
from sqlalchemy.orm import sessionmaker
from app.models.models import Schedule, Base
from app.core.database import SQLALCHEMY_DATABASE_URL

def update_database():
    # 데이터베이스 연결
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # parent_order 컬럼 추가
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE schedules ADD COLUMN parent_order INTEGER"))
            conn.commit()

        # 모든 부모 스케줄 ID 가져오기
        parent_ids = session.query(Schedule.parent_id).distinct().filter(
            Schedule.parent_id.isnot(None)
        ).all()
        
        # 각 부모별로 자식 스케줄 순서 업데이트
        for parent_id in parent_ids:
            parent_id = parent_id[0]  # 튜플에서 ID 추출
            children = session.query(Schedule).filter(
                Schedule.parent_id == parent_id
            ).order_by(Schedule.created_at).all()
            
            # 순서대로 parent_order 업데이트
            for index, child in enumerate(children, 1):
                child.parent_order = index
            
        session.commit()
        print("데이터베이스 업데이트가 완료되었습니다.")

    except Exception as e:
        session.rollback()
        print(f"오류 발생: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    update_database() 