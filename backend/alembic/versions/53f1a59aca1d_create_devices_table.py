"""create devices table

Revision ID: 53f1a59aca1d
Revises: 
Create Date: 2026-08-30 15:03:18.720645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53f1a59aca1d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('floor_id', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('firmware_version', sa.String(length=30), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['floor_id'], ['floors.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        op.f('ix_devices_device_id'),
        'devices',
        ['device_id'],
        unique=True
    )

    op.create_index(
        op.f('ix_devices_floor_id'),
        'devices',
        ['floor_id'],
        unique=False
    )

    op.create_index(
        op.f('ix_devices_id'),
        'devices',
        ['id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_devices_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_floor_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_device_id'), table_name='devices')
    op.drop_table('devices')