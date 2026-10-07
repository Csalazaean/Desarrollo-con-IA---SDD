"""add_soft_delete_and_password_reset

Revision ID: f2a89c1d3e4b
Revises: ec2fa45c2f9b
Create Date: 2026-10-05 23:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a89c1d3e4b'
down_revision = 'ec2fa45c2f9b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_deleted', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_tasks_is_deleted'), ['is_deleted'], unique=False)

    op.create_table('password_reset_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_password_reset_tokens_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_password_reset_tokens_token_hash'), ['token_hash'], unique=False)


def downgrade():
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_password_reset_tokens_token_hash'))
        batch_op.drop_index(batch_op.f('ix_password_reset_tokens_user_id'))
    op.drop_table('password_reset_tokens')

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tasks_is_deleted'))
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('is_deleted')
