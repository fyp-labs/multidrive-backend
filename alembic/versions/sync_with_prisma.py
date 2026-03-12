"""sync with prisma schema

Revision ID: sync_with_prisma
Revises: 932c882038be
Create Date: 2026-03-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'sync_with_prisma'
down_revision = '932c882038be'
branch_labels = None
depends_on = None


def upgrade():
    # Create enums
    role_enum = sa.Enum('ADMIN', 'USER', name='role')
    role_enum.create(op.get_bind(), checkfirst=True)

    cycle_enum = sa.Enum('monthly', 'yearly', name='subscriptioncycle')
    cycle_enum.create(op.get_bind(), checkfirst=True)

    tier_enum = sa.Enum('FREE', 'BASE', 'PRO', name='subscriptiontier')
    tier_enum.create(op.get_bind(), checkfirst=True)

    # Add missing columns to users table
    op.add_column('users', sa.Column('email_verified', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('role', sa.Enum('ADMIN', 'USER', name='role'), nullable=False, server_default='USER'))
    op.alter_column('users', 'password', existing_type=sa.String(), nullable=True)

    # Fix google_drive_accounts: expires_in Integer -> BigInteger, scope nullable
    op.alter_column('google_drive_accounts', 'expires_in',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    op.alter_column('google_drive_accounts', 'scope',
                    existing_type=sa.Text(),
                    nullable=True)

    # Create subscription_plans table
    op.create_table(
        'subscription_plans',
        sa.Column('uuid', sa.String(), primary_key=True),
        sa.Column('package_name', sa.String(), nullable=False),
        sa.Column('monthly_price', sa.Numeric(), nullable=True),
        sa.Column('yearly_price', sa.Numeric(), nullable=True),
        sa.Column('no_of_accounts', sa.Integer(), nullable=False),
        sa.Column('no_of_email_accounts', sa.Integer(), nullable=True),
        sa.Column('no_of_cloud_accounts', sa.Integer(), nullable=True),
        sa.Column('no_of_social_accounts', sa.Integer(), nullable=True),
        sa.Column('max_connected_drives', sa.Integer(), nullable=False),
        sa.Column('tier', sa.Enum('FREE', 'BASE', 'PRO', name='subscriptiontier'), nullable=False),
        sa.Column('action_limit', sa.Boolean(), nullable=False),
        sa.Column('cycle', sa.Enum('monthly', 'yearly', name='subscriptioncycle'), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Create subscribed_users table
    op.create_table(
        'subscribed_users',
        sa.Column('uuid', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('subscription_plan_id', sa.String(), sa.ForeignKey('subscription_plans.uuid', ondelete='CASCADE'), nullable=False),
        sa.Column('connected_accounts', sa.Integer(), nullable=False),
        sa.Column('connected_email_accounts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('connected_cloud_accounts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('connected_social_accounts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage', sa.Integer(), nullable=False),
        sa.Column('paid_amount', sa.Numeric(), nullable=True),
        sa.Column('sub_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sub_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Create otp_codes table
    op.create_table(
        'otp_codes',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('code', sa.String(), unique=True, nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_otp_codes_user_id', 'otp_codes', ['user_id'])


def downgrade():
    op.drop_index('ix_otp_codes_user_id', table_name='otp_codes')
    op.drop_table('otp_codes')
    op.drop_table('subscribed_users')
    op.drop_table('subscription_plans')

    op.drop_column('users', 'role')
    op.drop_column('users', 'email_verified')
    op.alter_column('users', 'password', existing_type=sa.String(), nullable=False)

    op.alter_column('google_drive_accounts', 'expires_in',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
    op.alter_column('google_drive_accounts', 'scope',
                    existing_type=sa.Text(),
                    nullable=False)

    sa.Enum(name='role').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='subscriptioncycle').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='subscriptiontier').drop(op.get_bind(), checkfirst=True)
