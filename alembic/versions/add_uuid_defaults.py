"""add database-level uuid defaults to id columns

Revision ID: add_uuid_defaults
Revises: sync_with_prisma
Create Date: 2026-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_uuid_defaults'
down_revision: Union[str, Sequence[str], None] = 'sync_with_prisma'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add database-level UUID defaults so Prisma can create rows without providing id
    op.alter_column('users', 'id',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('google_drive_accounts', 'id',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('google_drive_files', 'id',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('one_drive_accounts', 'id',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('one_drive_files', 'id',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('one_drive_folders', 'id',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('subscription_plans', 'uuid',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('subscribed_users', 'uuid',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('otp_codes', 'id',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('google_drive_document_embeddings', 'id',
        server_default=sa.text("gen_random_uuid()::text"))

    op.alter_column('google_drive_image_captions', 'id',
        server_default=sa.text("gen_random_uuid()::text"))


def downgrade() -> None:
    op.alter_column('google_drive_image_captions', 'id', server_default=None)
    op.alter_column('google_drive_document_embeddings', 'id', server_default=None)
    op.alter_column('otp_codes', 'id', server_default=None)
    op.alter_column('subscribed_users', 'uuid', server_default=None)
    op.alter_column('subscription_plans', 'uuid', server_default=None)
    op.alter_column('one_drive_folders', 'id', server_default=None)
    op.alter_column('one_drive_files', 'id', server_default=None)
    op.alter_column('one_drive_accounts', 'id', server_default=None)
    op.alter_column('google_drive_files', 'id', server_default=None)
    op.alter_column('google_drive_accounts', 'id', server_default=None)
    op.alter_column('users', 'id', server_default=None)
