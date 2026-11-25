"""device alarm limits and alert mode

Per-device alarm limits and a log-only mode, as described in the
Stage 2 design (per-device limits, log-only mode before alerting).

Revision ID: c3d5e7f9a1b2
Revises: 7b831cd9e102
Create Date: 2026-11-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d5e7f9a1b2'
down_revision: Union[str, Sequence[str], None] = '7b831cd9e102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    insp = sa.inspect(bind)
    if table_name not in insp.get_table_names():
        return False
    return column_name in [c['name'] for c in insp.get_columns(table_name)]


def upgrade() -> None:
    bind = op.get_bind()
    need_limits = not _column_exists(bind, 'devices', 'alarm_limits')
    need_mode = not _column_exists(bind, 'devices', 'alert_mode')
    if need_limits or need_mode:
        with op.batch_alter_table('devices') as batch_op:
            if need_limits:
                batch_op.add_column(sa.Column('alarm_limits', sa.JSON(), nullable=True))
            if need_mode:
                batch_op.add_column(
                    sa.Column('alert_mode', sa.String(length=20), nullable=False, server_default='alert')
                )


def downgrade() -> None:
    bind = op.get_bind()
    has_limits = _column_exists(bind, 'devices', 'alarm_limits')
    has_mode = _column_exists(bind, 'devices', 'alert_mode')
    if has_limits or has_mode:
        with op.batch_alter_table('devices') as batch_op:
            if has_mode:
                batch_op.drop_column('alert_mode')
            if has_limits:
                batch_op.drop_column('alarm_limits')
