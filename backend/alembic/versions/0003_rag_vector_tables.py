"""rag_vector_tables

Revision ID: 0003_rag_vector_tables
Revises: 0002_stage2_rbac_org
Create Date: 2025-01-01 00:00:02

Stage 5: pgvector + knowledge_documents + document_chunks
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_rag_vector_tables'
down_revision = '0002_stage2_rbac_org'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # knowledge_documents
    op.create_table(
        'knowledge_documents',
        sa.Column('id',            sa.Integer(), primary_key=True),
        sa.Column('org_id',        sa.Integer(), nullable=True),
        sa.Column('filename',      sa.String(255), nullable=False),
        sa.Column('original_name', sa.String(255), nullable=False),
        sa.Column('doc_type',      sa.String(50),  nullable=True),
        sa.Column('page_count',    sa.Integer(),   server_default='0'),
        sa.Column('chunk_count',   sa.Integer(),   server_default='0'),
        sa.Column('uploaded_by',   sa.Integer(),   nullable=True),
        sa.Column('uploaded_at',   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_knowledge_documents_org_id', 'knowledge_documents', ['org_id'])

    # document_chunks with vector column
    op.create_table(
        'document_chunks',
        sa.Column('id',          sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('org_id',      sa.Integer(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('content',     sa.Text(),    nullable=False),
        sa.Column('token_count', sa.Integer(), server_default='0'),
    )

    # Add vector column separately (pgvector type not in base SQLAlchemy)
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")

    # IVFFlat index for fast cosine similarity search
    op.execute("""
        CREATE INDEX ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    op.create_index('ix_document_chunks_org_id',      'document_chunks', ['org_id'])
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])

    # intent_audit table
    op.create_table(
        'intent_audit',
        sa.Column('id',              sa.Integer(), primary_key=True),
        sa.Column('org_id',          sa.Integer(), nullable=True),
        sa.Column('user_id',         sa.Integer(), nullable=True),
        sa.Column('message',         sa.Text(),    nullable=False),
        sa.Column('detected_intent', sa.String(100), nullable=True),
        sa.Column('confidence',      sa.Float(),   nullable=True),
        sa.Column('action_type',     sa.String(50), nullable=True),
        sa.Column('was_correct',     sa.Boolean(), nullable=True),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # vision_analyses table
    op.create_table(
        'vision_analyses',
        sa.Column('id',                 sa.Integer(), primary_key=True),
        sa.Column('org_id',             sa.Integer(), nullable=True),
        sa.Column('user_id',            sa.Integer(), nullable=True),
        sa.Column('image_filename',     sa.String(255), nullable=True),
        sa.Column('analysis_type',      sa.String(50),  nullable=True),
        sa.Column('findings',           sa.JSON(),      nullable=True),
        sa.Column('defect_rate',        sa.Float(),     nullable=True),
        sa.Column('confidence',         sa.Float(),     nullable=True),
        sa.Column('recommended_action', sa.Text(),      nullable=True),
        sa.Column('summary',            sa.Text(),      nullable=True),
        sa.Column('created_at',         sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    pass
