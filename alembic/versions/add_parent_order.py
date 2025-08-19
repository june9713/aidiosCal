"""add parent_order column

Revision ID: add_parent_order
Revises: 
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'add_parent_order'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # parent_order 컬럼 추가
    op.add_column('schedules', sa.Column('parent_order', sa.Integer(), nullable=True))
    
    # 기존 데이터 업데이트
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE schedules 
        SET parent_order = (
            SELECT COUNT(*) 
            FROM schedules s2 
            WHERE s2.parent_id = schedules.parent_id 
            AND s2.created_at <= schedules.created_at
        )
        WHERE parent_id IS NOT NULL
    """))

def downgrade():
    op.drop_column('schedules', 'parent_order') 