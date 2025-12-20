"""add_password_and_role_to_counsellors

Revision ID: 0578ecab030b
Revises: ebb27f7222d5
Create Date: 2025-12-20 10:11:17.588606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0578ecab030b'
down_revision: Union[str, None] = 'ebb27f7222d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type if it doesn't exist
    role_enum = sa.Enum('user', 'admin', 'super-admin', name='role')
    role_enum.create(op.get_bind(), checkfirst=True)
    
    # Add password column (nullable for existing records)
    op.add_column('counsellors', sa.Column('password', sa.String(), nullable=True))
    
    # Add role column with default value 'user'
    op.add_column('counsellors', sa.Column('role', role_enum, nullable=False, server_default='user'))


def downgrade() -> None:
    # Remove role column
    op.drop_column('counsellors', 'role')
    
    # Remove password column
    op.drop_column('counsellors', 'password')
    
    # Drop the enum type (only if not used elsewhere)
    # op.execute('DROP TYPE role')
