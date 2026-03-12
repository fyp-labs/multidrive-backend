"""add uuid defaults to all id columns

Revision ID: add_uuid_defaults
Revises: sync_with_prisma
Create Date: 2026-03-08 00:01:00.000000
"""
from alembic import op

revision = 'add_uuid_defaults'
down_revision = 'sync_with_prisma'
branch_labels = None
depends_on = None

# All (table, column) pairs that need gen_random_uuid()::text defaults
ID_COLUMNS = [
    ('users', 'id'),
    ('google_drive_accounts', 'id'),
    ('google_drive_files', 'id'),
    ('google_drive_folders', 'id'),
    ('google_drive_folder_trees', 'id'),
    ('one_drive_accounts', 'id'),
    ('one_drive_files', 'id'),
    ('one_drive_folders', 'id'),
    ('one_drive_folder_trees', 'id'),
    ('subscription_plans', 'uuid'),
    ('subscribed_users', 'uuid'),
    ('otp_codes', 'id'),
]


def upgrade():
    for table, col in ID_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} SET DEFAULT gen_random_uuid()::text"
        )


def downgrade():
    for table, col in ID_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} DROP DEFAULT"
        )
