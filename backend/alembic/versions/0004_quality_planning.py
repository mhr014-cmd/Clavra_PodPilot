"""quality_planning_tables

Revision ID: 0004_quality_planning
Revises: 0003_rag_vector_tables
Create Date: 2025-01-01 00:00:03
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_quality_planning'
down_revision = '0003_rag_vector_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'quality_reports',
        sa.Column('id',              sa.Integer(), primary_key=True),
        sa.Column('order_id',        sa.Integer(), nullable=True),
        sa.Column('line_id',         sa.Integer(), nullable=True),
        sa.Column('org_id',          sa.Integer(), nullable=True),
        sa.Column('inspector_id',    sa.Integer(), nullable=True),
        sa.Column('defect_type',     sa.String(200), nullable=True),
        sa.Column('defect_count',    sa.Integer(),   server_default='0'),
        sa.Column('total_checked',   sa.Integer(),   server_default='0'),
        sa.Column('defect_rate',     sa.Float(),     server_default='0'),
        sa.Column('severity',        sa.String(50),  server_default='minor'),
        sa.Column('notes',           sa.Text(),      nullable=True),
        sa.Column('inspection_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_quality_reports_org_id', 'quality_reports', ['org_id'])

    op.create_table(
        'planning_tna',
        sa.Column('id',           sa.Integer(), primary_key=True),
        sa.Column('order_id',     sa.Integer(), nullable=True),
        sa.Column('org_id',       sa.Integer(), nullable=True),
        sa.Column('task_name',    sa.String(300), nullable=False),
        sa.Column('responsible',  sa.String(200), nullable=True),
        sa.Column('planned_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_date',  sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_completed', sa.Boolean(),  server_default='false'),
        sa.Column('notes',        sa.Text(),     nullable=True),
        sa.Column('created_at',   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_planning_tna_org_id', 'planning_tna', ['org_id'])


def downgrade() -> None:
    pass
