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


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    insp = sa.inspect(bind)
    if table_name not in insp.get_table_names():
        return False
    columns = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in columns


def _fk_exists(bind, table_name: str, constrained_col: str, ref_table: str) -> bool:
    insp = sa.inspect(bind)
    if table_name not in insp.get_table_names():
        return False
    return any(
        constrained_col in fk.get('constrained_columns', []) and fk.get('referred_table') == ref_table
        for fk in insp.get_foreign_keys(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    need_block_col = not _column_exists(bind, 'users', 'assigned_block_id')
    need_block_fk = not _fk_exists(bind, 'users', 'assigned_block_id', 'blocks')
    need_floor_col = not _column_exists(bind, 'users', 'assigned_floor_id')
    need_floor_fk = not _fk_exists(bind, 'users', 'assigned_floor_id', 'floors')

    if need_block_col or need_block_fk or need_floor_col or need_floor_fk:
        with op.batch_alter_table('users') as batch_op:
            if need_block_col:
                batch_op.add_column(sa.Column('assigned_block_id', sa.Integer(), nullable=True))
            if need_block_fk:
                batch_op.create_foreign_key('fk_users_assigned_block_id_blocks', 'blocks', ['assigned_block_id'], ['id'])
            if need_floor_col:
                batch_op.add_column(sa.Column('assigned_floor_id', sa.Integer(), nullable=True))
            if need_floor_fk:
                batch_op.create_foreign_key('fk_users_assigned_floor_id_floors', 'floors', ['assigned_floor_id'], ['id'])


def downgrade() -> None:
    bind = op.get_bind()
    has_block_col = _column_exists(bind, 'users', 'assigned_block_id')
    has_block_fk = _fk_exists(bind, 'users', 'assigned_block_id', 'blocks')
    has_floor_col = _column_exists(bind, 'users', 'assigned_floor_id')
    has_floor_fk = _fk_exists(bind, 'users', 'assigned_floor_id', 'floors')

    if has_block_col or has_block_fk or has_floor_col or has_floor_fk:
        with op.batch_alter_table('users') as batch_op:
            if has_floor_fk:
                batch_op.drop_constraint('fk_users_assigned_floor_id_floors', type_='foreignkey')
            if has_floor_col:
                batch_op.drop_column('assigned_floor_id')
            if has_block_fk:
                batch_op.drop_constraint('fk_users_assigned_block_id_blocks', type_='foreignkey')
            if has_block_col:
                batch_op.drop_column('assigned_block_id')
