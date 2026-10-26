"""add_user_location_scope

Revision ID: 7b831cd9e102
Revises: 4a921bc8c9a8
Create Date: 2026-10-22 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b831cd9e102'
down_revision: Union[str, Sequence[str], None] = '4a921bc8c9a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('assigned_block_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('assigned_floor_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'assigned_floor_id')
    op.drop_column('users', 'assigned_block_id')
