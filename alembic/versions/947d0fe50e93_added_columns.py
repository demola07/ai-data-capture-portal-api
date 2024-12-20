"""added columns

Revision ID: 947d0fe50e93
Revises: db018d07cf7f
Create Date: 2024-12-20 00:20:26.504736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '947d0fe50e93'
down_revision: Union[str, None] = 'db018d07cf7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'counsellee', ['email'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'counsellee', type_='unique')
    # ### end Alembic commands ###
