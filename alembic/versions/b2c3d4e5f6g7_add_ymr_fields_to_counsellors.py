"""add_ymr_fields_to_counsellors

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-21 00:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename will_attend_ymr_2024 to will_attend_ymr
    op.alter_column('counsellors', 'will_attend_ymr_2024', new_column_name='will_attend_ymr')
    
    # Add is_available_for_training column with default True
    op.add_column('counsellors', sa.Column('is_available_for_training', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    # Remove is_available_for_training column
    op.drop_column('counsellors', 'is_available_for_training')
    
    # Rename back to will_attend_ymr_2024
    op.alter_column('counsellors', 'will_attend_ymr', new_column_name='will_attend_ymr_2024')
