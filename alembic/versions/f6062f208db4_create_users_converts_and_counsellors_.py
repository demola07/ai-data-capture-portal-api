"""create users, converts and counsellors tables

Revision ID: f6062f208db4
Revises: 
Create Date: 2024-12-17 00:56:29.672123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6062f208db4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('converts',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('gender', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('phone_number', sa.String(), nullable=True),
    sa.Column('date_of_birth', sa.String(), nullable=True),
    sa.Column('relationship_status', sa.String(), nullable=True),
    sa.Column('country', sa.String(), nullable=True),
    sa.Column('state', sa.String(), nullable=True),
    sa.Column('address', sa.String(), nullable=True),
    sa.Column('nearest_bus_stop', sa.String(), nullable=True),
    sa.Column('is_student', sa.Boolean(), server_default='FALSE', nullable=True),
    sa.Column('age_group', sa.String(), nullable=True),
    sa.Column('school', sa.String(), nullable=True),
    sa.Column('occupation', sa.String(), nullable=True),
    sa.Column('denomination', sa.String(), nullable=True),
    sa.Column('availability_for_follow_up', sa.Boolean(), server_default='TRUE', nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('counsellors',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('phone_number', sa.String(), nullable=True),
    sa.Column('gender', sa.String(), nullable=True),
    sa.Column('date_of_birth', sa.String(), nullable=True),
    sa.Column('address', sa.String(), nullable=True),
    sa.Column('years_of_experience', sa.Integer(), nullable=True),
    sa.Column('has_certification', sa.Boolean(), nullable=False),
    sa.Column('denomination', sa.String(length=100), nullable=True),
    sa.Column('will_attend_ymr_2024', sa.Boolean(), nullable=False),
    sa.Column('is_available_for_training', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password', sa.String(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('role', sa.Enum('USER', 'ADMIN', 'SUPERADMIN', name='role'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users')
    op.drop_table('counsellors')
    op.drop_table('converts')
    # ### end Alembic commands ###
