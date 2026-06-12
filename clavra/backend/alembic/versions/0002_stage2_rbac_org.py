"""stage2_rbac_org

Revision ID: 0002_stage2_rbac_org
Revises: 9a2ba3c27ae0
Create Date: 2025-01-01 00:00:00.000000

Stage 2 migration:
- Create organizations table
- Add full_name, org_id, refresh_token_hash, is_active, is_verified,
  last_login_at, updated_at to users
- Rename users.password → password_hash
- Add org_id, timestamps, produced_qty, line_id to production_orders
- Add org_id, eta, timestamps to shipments
- Add org_id, user_id, intent, confidence, action_type to ai_messages
- Add org_id, user_id to ai_conversations
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_stage2_rbac_org'
down_revision = '41b70be6c647'
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── organizations ─────────────────────────────────────────────────────
    op.create_table(
        'organizations',
        sa.Column('id',         sa.Integer(),     primary_key=True),
        sa.Column('name',       sa.String(200),   nullable=False),
        sa.Column('slug',       sa.String(100),   unique=True, nullable=False),
        sa.Column('plan',       sa.String(50),    server_default='starter'),
        sa.Column('is_active',  sa.Boolean(),     server_default='true'),
        sa.Column('max_users',  sa.Integer(),     server_default='10'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # ── users — add columns (never drop old ones) ─────────────────────────
    op.add_column('users', sa.Column('full_name',           sa.String(200), nullable=True))
    op.add_column('users', sa.Column('password_hash',       sa.String(255), nullable=True))
    op.add_column('users', sa.Column('org_id',              sa.Integer(),   nullable=True))
    op.add_column('users', sa.Column('refresh_token_hash',  sa.String(255), nullable=True))
    op.add_column('users', sa.Column('is_active',           sa.Boolean(),   server_default='true'))
    op.add_column('users', sa.Column('is_verified',         sa.Boolean(),   server_default='false'))
    op.add_column('users', sa.Column('last_login_at',       sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('created_at',          sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('users', sa.Column('updated_at',          sa.DateTime(timezone=True), server_default=sa.func.now()))

    # Copy existing password → password_hash
    op.execute("UPDATE users SET password_hash = password WHERE password_hash IS NULL")
    op.execute("UPDATE users SET full_name = email WHERE full_name IS NULL")

    # ── production_orders ─────────────────────────────────────────────────
    op.add_column('production_orders', sa.Column('org_id',        sa.Integer(),   nullable=True))
    op.add_column('production_orders', sa.Column('produced_qty',  sa.Integer(),   server_default='0'))
    op.add_column('production_orders', sa.Column('defect_qty',    sa.Integer(),   server_default='0'))
    op.add_column('production_orders', sa.Column('line_id',       sa.Integer(),   nullable=True))
    op.add_column('production_orders', sa.Column('start_date',    sa.DateTime(timezone=True), nullable=True))
    op.add_column('production_orders', sa.Column('end_date',      sa.DateTime(timezone=True), nullable=True))
    op.add_column('production_orders', sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('production_orders', sa.Column('created_by',    sa.Integer(),   nullable=True))
    op.add_column('production_orders', sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('production_orders', sa.Column('updated_at',    sa.DateTime(timezone=True), server_default=sa.func.now()))

    # ── shipments ─────────────────────────────────────────────────────────
    op.add_column('shipments', sa.Column('org_id',           sa.Integer(),  nullable=True))
    op.add_column('shipments', sa.Column('carrier',          sa.String(200), nullable=True))
    op.add_column('shipments', sa.Column('port_of_loading',  sa.String(200), nullable=True))
    op.add_column('shipments', sa.Column('order_id',         sa.Integer(),  nullable=True))
    op.add_column('shipments', sa.Column('eta',              sa.DateTime(timezone=True), nullable=True))
    op.add_column('shipments', sa.Column('actual_departure', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shipments', sa.Column('actual_arrival',   sa.DateTime(timezone=True), nullable=True))
    op.add_column('shipments', sa.Column('created_by',       sa.Integer(),  nullable=True))
    op.add_column('shipments', sa.Column('created_at',       sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('shipments', sa.Column('updated_at',       sa.DateTime(timezone=True), server_default=sa.func.now()))

    # ── ai_conversations ──────────────────────────────────────────────────
    op.add_column('ai_conversations', sa.Column('user_id',    sa.Integer(), nullable=True))
    op.add_column('ai_conversations', sa.Column('org_id',     sa.Integer(), nullable=True))
    op.add_column('ai_conversations', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))

    # ── ai_messages ───────────────────────────────────────────────────────
    op.add_column('ai_messages', sa.Column('intent',      sa.String(100), nullable=True))
    op.add_column('ai_messages', sa.Column('confidence',  sa.Float(),     nullable=True))
    op.add_column('ai_messages', sa.Column('action_type', sa.String(50),  nullable=True))
    op.add_column('ai_messages', sa.Column('sql_used',    sa.Text(),      nullable=True))
    op.add_column('ai_messages', sa.Column('sources',     sa.JSON(),      nullable=True))
    op.add_column('ai_messages', sa.Column('org_id',      sa.Integer(),   nullable=True))
    op.add_column('ai_messages', sa.Column('user_id',     sa.Integer(),   nullable=True))


def downgrade() -> None:
    # Intentionally minimal — we never drop in production
    pass
