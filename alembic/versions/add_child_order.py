"""add child_order column

Revision ID: add_child_order
Revises: 
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.models.models import Schedule

# revision identifiers, used by Alembic.
revision = 'add_child_order'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # child_order 컬럼 추가
    op.add_column('schedules', sa.Column('child_order', sa.Integer(), nullable=True))
    
    # 세션 생성
    bind = op.get_bind()
    session = Session(bind=bind)
    
    try:
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
            
            # 순서대로 child_order 업데이트
            for index, child in enumerate(children, 1):
                child.child_order = index
            
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def downgrade():
    # child_order 컬럼 제거
    op.drop_column('schedules', 'child_order') 