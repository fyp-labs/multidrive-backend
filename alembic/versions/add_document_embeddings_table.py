"""add document embeddings table

Revision ID: add_document_embeddings
Revises: add_image_captions
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_document_embeddings'
down_revision = 'add_image_captions'
branch_label = None
depends_on = None


def upgrade() -> None:
    # Create google_drive_document_embeddings table
    op.create_table(
        'google_drive_document_embeddings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('google_drive_account_id', sa.String(), nullable=False),
        sa.Column('file_id', sa.String(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('text_preview', sa.Text(), nullable=True),
        sa.Column('chroma_doc_id', sa.String(), nullable=False),
        sa.Column('extraction_metadata', postgresql.JSON(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['google_drive_account_id'], ['google_drive_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['google_drive_files.file_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('file_id'),
        sa.UniqueConstraint('chroma_doc_id')
    )
    
    # Create indexes for better query performance
    op.create_index(
        'idx_document_embeddings_user_account',
        'google_drive_document_embeddings',
        ['user_id', 'google_drive_account_id']
    )
    op.create_index(
        'idx_document_embeddings_file_id',
        'google_drive_document_embeddings',
        ['file_id']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_document_embeddings_file_id', table_name='google_drive_document_embeddings')
    op.drop_index('idx_document_embeddings_user_account', table_name='google_drive_document_embeddings')
    
    # Drop table
    op.drop_table('google_drive_document_embeddings')
