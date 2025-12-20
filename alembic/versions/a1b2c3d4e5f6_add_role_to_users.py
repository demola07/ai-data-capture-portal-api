"""add_role_to_users

Revision ID: a1b2c3d4e5f6
Revises: 0578ecab030b
Create Date: 2025-12-21 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0578ecab030b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The role enum already exists from the counsellors migration
    # Just add the role column to users table
    op.add_column('users', sa.Column('role', sa.Enum('user', 'admin', 'super-admin', name='role'), nullable=False, server_default='user'))


def downgrade() -> None:
    # Remove role column from users
    op.drop_column('users', 'role')
