"""add_missing_columns

Revision ID: 4a921bc8c9a8
Revises: 53f1a59aca1d
Create Date: 2026-09-30 22:58:47.111451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a921bc8c9a8'
down_revision: Union[str, Sequence[str], None] = '53f1a59aca1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    insp = sa.inspect(bind)
    if table_name not in insp.get_table_names():
        return False
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in columns


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    insp = sa.inspect(bind)
    if table_name not in insp.get_table_names():
        return False
    return any(idx.get("name") == index_name for idx in insp.get_indexes(table_name))


def upgrade() -> None:
    """Upgrade schema with idempotency checks."""
    bind = op.get_bind()

    # devices
    if not _column_exists(bind, 'devices', 'last_seen_at'):
        op.add_column('devices', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    if not _column_exists(bind, 'devices', 'ingest_key'):
        op.add_column('devices', sa.Column('ingest_key', sa.String(length=80), nullable=True))

    # faults
    if not _column_exists(bind, 'faults', 'category'):
        op.add_column('faults', sa.Column('category', sa.String(length=30), server_default='electrical', nullable=False))
    if not _column_exists(bind, 'faults', 'measured_value'):
        op.add_column('faults', sa.Column('measured_value', sa.Float(), nullable=True))
    if not _column_exists(bind, 'faults', 'expected_value'):
        op.add_column('faults', sa.Column('expected_value', sa.Float(), nullable=True))
    if not _column_exists(bind, 'faults', 'unit'):
        op.add_column('faults', sa.Column('unit', sa.String(length=20), nullable=True))
    if not _index_exists(bind, 'faults', 'ix_faults_category'):
        op.create_index(op.f('ix_faults_category'), 'faults', ['category'], unique=False)

    # relays
    if not _column_exists(bind, 'relays', 'gpio_pin'):
        op.add_column('relays', sa.Column('gpio_pin', sa.Integer(), nullable=True))
    if not _column_exists(bind, 'relays', 'commanded_state'):
        op.add_column('relays', sa.Column('commanded_state', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    if not _column_exists(bind, 'relays', 'actual_state'):
        op.add_column('relays', sa.Column('actual_state', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    if _column_exists(bind, 'relays', 'actual_state'):
        op.drop_column('relays', 'actual_state')
    if _column_exists(bind, 'relays', 'commanded_state'):
        op.drop_column('relays', 'commanded_state')
    if _column_exists(bind, 'relays', 'gpio_pin'):
        op.drop_column('relays', 'gpio_pin')
    if _index_exists(bind, 'faults', 'ix_faults_category'):
        op.drop_index(op.f('ix_faults_category'), table_name='faults')
    if _column_exists(bind, 'faults', 'unit'):
        op.drop_column('faults', 'unit')
    if _column_exists(bind, 'faults', 'expected_value'):
        op.drop_column('faults', 'expected_value')
    if _column_exists(bind, 'faults', 'measured_value'):
        op.drop_column('faults', 'measured_value')
    if _column_exists(bind, 'faults', 'category'):
        op.drop_column('faults', 'category')
    if _column_exists(bind, 'devices', 'ingest_key'):
        op.drop_column('devices', 'ingest_key')
    if _column_exists(bind, 'devices', 'last_seen_at'):
        op.drop_column('devices', 'last_seen_at')
