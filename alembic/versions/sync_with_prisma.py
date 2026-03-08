"""sync schema with prisma - add enums, subscription, otp, user fields, fix types

Revision ID: sync_with_prisma
Revises: add_document_embeddings
Create Date: 2026-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'sync_with_prisma'
down_revision: Union[str, Sequence[str], None] = 'add_document_embeddings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create enums
    role_enum = postgresql.ENUM('ADMIN', 'USER', name='Role', create_type=False)
    role_enum.create(op.get_bind(), checkfirst=True)

    subscription_cycle_enum = postgresql.ENUM('monthly', 'yearly', name='SubscriptionCycle', create_type=False)
    subscription_cycle_enum.create(op.get_bind(), checkfirst=True)

    subscription_tier_enum = postgresql.ENUM('FREE', 'BASE', 'PRO', name='SubscriptionTier', create_type=False)
    subscription_tier_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add missing columns to users table
    op.add_column('users', sa.Column('email_verified', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('role',
        postgresql.ENUM('ADMIN', 'USER', name='Role', create_type=False),
        server_default='USER',
        nullable=False
    ))

    # 3. Fix google_drive_accounts: expires_in Integer -> BigInteger
    op.alter_column('google_drive_accounts', 'expires_in',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False
    )

    # 4. Fix google_drive_accounts: scope non-nullable -> nullable
    op.alter_column('google_drive_accounts', 'scope',
        existing_type=sa.Text(),
        nullable=True
    )

    # 5. Create subscription_plans table
    op.create_table('subscription_plans',
        sa.Column('uuid', sa.String(), nullable=False),
        sa.Column('package_name', sa.String(), nullable=False),
        sa.Column('monthly_price', sa.Numeric(), nullable=True),
        sa.Column('yearly_price', sa.Numeric(), nullable=True),
        sa.Column('no_of_accounts', sa.Integer(), nullable=False),
        sa.Column('no_of_email_accounts', sa.Integer(), nullable=True),
        sa.Column('no_of_cloud_accounts', sa.Integer(), nullable=True),
        sa.Column('no_of_social_accounts', sa.Integer(), nullable=True),
        sa.Column('max_connected_drives', sa.Integer(), nullable=False),
        sa.Column('tier', postgresql.ENUM('FREE', 'BASE', 'PRO', name='SubscriptionTier', create_type=False), nullable=False),
        sa.Column('action_limit', sa.Boolean(), nullable=False),
        sa.Column('cycle', postgresql.ENUM('monthly', 'yearly', name='SubscriptionCycle', create_type=False), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('uuid')
    )

    # 6. Create subscribed_users table
    op.create_table('subscribed_users',
        sa.Column('uuid', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('subscription_plan_id', sa.String(), nullable=False),
        sa.Column('connected_accounts', sa.Integer(), nullable=False),
        sa.Column('connected_email_accounts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('connected_cloud_accounts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('connected_social_accounts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('usage', sa.Integer(), nullable=False),
        sa.Column('paid_amount', sa.Numeric(), nullable=True),
        sa.Column('sub_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sub_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_plan_id'], ['subscription_plans.uuid'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('uuid'),
        sa.UniqueConstraint('user_id')
    )

    # 7. Create otp_codes table
    op.create_table('otp_codes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_otp_codes_user_id'), 'otp_codes', ['user_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_otp_codes_user_id'), table_name='otp_codes')
    op.drop_table('otp_codes')
    op.drop_table('subscribed_users')
    op.drop_table('subscription_plans')

    # Revert google_drive_accounts changes
    op.alter_column('google_drive_accounts', 'scope',
        existing_type=sa.Text(),
        nullable=False
    )
    op.alter_column('google_drive_accounts', 'expires_in',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False
    )

    # Remove columns from users
    op.drop_column('users', 'role')
    op.drop_column('users', 'email_verified')

    # Drop enums
    postgresql.ENUM(name='SubscriptionTier').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='SubscriptionCycle').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='Role').drop(op.get_bind(), checkfirst=True)
