"""add image captions table

Revision ID: add_image_captions
Revises: 
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_image_captions'
down_revision = '932c882038be'  # Points to the latest migration
branch_label = None
depends_on = None


def upgrade() -> None:
    # Create google_drive_image_captions table
    op.create_table(
        'google_drive_image_captions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('google_drive_account_id', sa.String(), nullable=False),
        sa.Column('file_id', sa.String(), nullable=False),
        sa.Column('caption', sa.Text(), nullable=False),
        sa.Column('chroma_doc_id', sa.String(), nullable=False),
        sa.Column('file_metadata', postgresql.JSON(), nullable=True),
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
        'idx_image_captions_user_account',
        'google_drive_image_captions',
        ['user_id', 'google_drive_account_id']
    )
    op.create_index(
        'idx_image_captions_file_id',
        'google_drive_image_captions',
        ['file_id']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_image_captions_file_id', table_name='google_drive_image_captions')
    op.drop_index('idx_image_captions_user_account', table_name='google_drive_image_captions')
    
    # Drop table
    op.drop_table('google_drive_image_captions')
