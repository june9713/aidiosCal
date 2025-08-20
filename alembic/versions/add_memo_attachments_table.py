"""add memo attachments table

Revision ID: add_memo_attachments_table
Revises: 99b92b697c36
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_memo_attachments_table'
down_revision = '99b92b697c36'
branch_labels = None
depends_on = None


def upgrade():
    # 메모 첨부파일 테이블 생성
    op.create_table('memo_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=False),
        sa.Column('attachment_type', sa.String(), nullable=False),
        sa.Column('reference_id', sa.Integer(), nullable=False),
        sa.Column('uploader_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 인덱스 생성
    op.create_index(op.f('ix_memo_attachments_id'), 'memo_attachments', ['id'], unique=False)
    op.create_index(op.f('ix_memo_attachments_attachment_type'), 'memo_attachments', ['attachment_type'], unique=False)
    op.create_index(op.f('ix_memo_attachments_reference_id'), 'memo_attachments', ['reference_id'], unique=False)


def downgrade():
    # 인덱스 삭제
    op.drop_index(op.f('ix_memo_attachments_reference_id'), table_name='memo_attachments')
    op.drop_index(op.f('ix_memo_attachments_attachment_type'), table_name='memo_attachments')
    op.drop_index(op.f('ix_memo_attachments_id'), table_name='memo_attachments')
    
    # 테이블 삭제
    op.drop_table('memo_attachments')
