"""create initial tables and devices

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


def _table_exists(bind, table_name: str) -> bool:
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names()


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


def _ensure_table(bind, table_name: str, create_fn, required_columns: list, required_indexes: list):
    """Ensure table exists, or create missing columns and indexes if partially initialized."""
    if not _table_exists(bind, table_name):
        create_fn()
        return

    # If table already exists, verify that all expected baseline columns exist
    for col in required_columns:
        if not _column_exists(bind, table_name, col.name):
            op.add_column(table_name, col)

    # Verify that all expected baseline indexes exist
    for idx_name, col_names, is_unique in required_indexes:
        if not _index_exists(bind, table_name, idx_name):
            op.create_index(op.f(idx_name), table_name, col_names, unique=is_unique)


def upgrade() -> None:
    """Upgrade schema in topological order with column-level healing."""
    bind = op.get_bind()

    # 1. colleges
    def _create_colleges():
        op.create_table(
            'colleges',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=150), nullable=False),
            sa.Column('code', sa.String(length=30), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
            sa.UniqueConstraint('code')
        )
        op.create_index(op.f('ix_colleges_id'), 'colleges', ['id'], unique=False)

    _ensure_table(
        bind,
        'colleges',
        _create_colleges,
        required_columns=[
            sa.Column('name', sa.String(length=150), nullable=False, server_default=''),
            sa.Column('code', sa.String(length=30), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        ],
        required_indexes=[('ix_colleges_id', ['id'], False)]
    )

    # 2. blocks
    def _create_blocks():
        op.create_table(
            'blocks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('college_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('code', sa.String(length=30), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.ForeignKeyConstraint(['college_id'], ['colleges.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_blocks_id'), 'blocks', ['id'], unique=False)
        op.create_index(op.f('ix_blocks_college_id'), 'blocks', ['college_id'], unique=False)

    _ensure_table(
        bind,
        'blocks',
        _create_blocks,
        required_columns=[
            sa.Column('college_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('name', sa.String(length=100), nullable=False, server_default=''),
            sa.Column('code', sa.String(length=30), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        ],
        required_indexes=[
            ('ix_blocks_id', ['id'], False),
            ('ix_blocks_college_id', ['college_id'], False),
        ]
    )

    # 3. floors
    def _create_floors():
        op.create_table(
            'floors',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('block_id', sa.Integer(), nullable=False),
            sa.Column('floor_number', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.ForeignKeyConstraint(['block_id'], ['blocks.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_floors_id'), 'floors', ['id'], unique=False)
        op.create_index(op.f('ix_floors_block_id'), 'floors', ['block_id'], unique=False)

    _ensure_table(
        bind,
        'floors',
        _create_floors,
        required_columns=[
            sa.Column('block_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('floor_number', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('name', sa.String(length=100), nullable=False, server_default=''),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        ],
        required_indexes=[
            ('ix_floors_id', ['id'], False),
            ('ix_floors_block_id', ['block_id'], False),
        ]
    )

    # 4. devices (initial baseline columns)
    def _create_devices():
        op.create_table(
            'devices',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('device_id', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('floor_id', sa.Integer(), nullable=True),
            sa.Column('location', sa.String(length=100), nullable=True),
            sa.Column('firmware_version', sa.String(length=30), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.ForeignKeyConstraint(['floor_id'], ['floors.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_devices_id'), 'devices', ['id'], unique=False)
        op.create_index(op.f('ix_devices_device_id'), 'devices', ['device_id'], unique=True)
        op.create_index(op.f('ix_devices_floor_id'), 'devices', ['floor_id'], unique=False)

    _ensure_table(
        bind,
        'devices',
        _create_devices,
        required_columns=[
            sa.Column('device_id', sa.String(length=50), nullable=False, server_default=''),
            sa.Column('name', sa.String(length=100), nullable=False, server_default=''),
            sa.Column('floor_id', sa.Integer(), nullable=True),
            sa.Column('location', sa.String(length=100), nullable=True),
            sa.Column('firmware_version', sa.String(length=30), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        ],
        required_indexes=[
            ('ix_devices_id', ['id'], False),
            ('ix_devices_device_id', ['device_id'], True),
            ('ix_devices_floor_id', ['floor_id'], False),
        ]
    )

    # 5. telemetry
    def _create_telemetry():
        op.create_table(
            'telemetry',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('device_id', sa.Integer(), nullable=False),
            sa.Column('phase', sa.String(length=10), nullable=False),
            sa.Column('voltage', sa.Float(), nullable=True),
            sa.Column('current', sa.Float(), nullable=True),
            sa.Column('power', sa.Float(), nullable=True),
            sa.Column('energy', sa.Float(), nullable=True),
            sa.Column('power_factor', sa.Float(), nullable=True),
            sa.Column('frequency', sa.Float(), nullable=True),
            sa.Column('temperature', sa.Float(), nullable=True),
            sa.Column('sampled_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('sampling_interval_ms', sa.Integer(), nullable=True),
            sa.Column('transmission_reason', sa.String(length=30), nullable=False),
            sa.Column('source', sa.String(length=20), nullable=False),
            sa.Column('data_quality', sa.String(length=20), nullable=True),
            sa.ForeignKeyConstraint(['device_id'], ['devices.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_telemetry_id'), 'telemetry', ['id'], unique=False)
        op.create_index(op.f('ix_telemetry_device_id'), 'telemetry', ['device_id'], unique=False)
        op.create_index(op.f('ix_telemetry_sampled_at'), 'telemetry', ['sampled_at'], unique=False)
        op.create_index(op.f('ix_telemetry_received_at'), 'telemetry', ['received_at'], unique=False)

    _ensure_table(
        bind,
        'telemetry',
        _create_telemetry,
        required_columns=[
            sa.Column('device_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('phase', sa.String(length=10), nullable=False, server_default='R'),
            sa.Column('voltage', sa.Float(), nullable=True),
            sa.Column('current', sa.Float(), nullable=True),
            sa.Column('power', sa.Float(), nullable=True),
            sa.Column('energy', sa.Float(), nullable=True),
            sa.Column('power_factor', sa.Float(), nullable=True),
            sa.Column('frequency', sa.Float(), nullable=True),
            sa.Column('temperature', sa.Float(), nullable=True),
            sa.Column('sampled_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('sampling_interval_ms', sa.Integer(), nullable=True),
            sa.Column('transmission_reason', sa.String(length=30), nullable=False, server_default='SCHEDULED'),
            sa.Column('source', sa.String(length=20), nullable=False, server_default='REAL'),
            sa.Column('data_quality', sa.String(length=20), nullable=True),
        ],
        required_indexes=[
            ('ix_telemetry_id', ['id'], False),
            ('ix_telemetry_device_id', ['device_id'], False),
            ('ix_telemetry_sampled_at', ['sampled_at'], False),
            ('ix_telemetry_received_at', ['received_at'], False),
        ]
    )

    # 6. relays (initial baseline schema)
    def _create_relays():
        op.create_table(
            'relays',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('device_id', sa.Integer(), nullable=False),
            sa.Column('relay_number', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('is_on', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.ForeignKeyConstraint(['device_id'], ['devices.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_relays_id'), 'relays', ['id'], unique=False)
        op.create_index(op.f('ix_relays_device_id'), 'relays', ['device_id'], unique=False)

    _ensure_table(
        bind,
        'relays',
        _create_relays,
        required_columns=[
            sa.Column('device_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('relay_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('name', sa.String(length=100), nullable=False, server_default=''),
            sa.Column('is_on', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        ],
        required_indexes=[
            ('ix_relays_id', ['id'], False),
            ('ix_relays_device_id', ['device_id'], False),
        ]
    )

    # 7. faults (initial baseline schema)
    def _create_faults():
        op.create_table(
            'faults',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('device_id', sa.Integer(), nullable=False),
            sa.Column('phase', sa.String(length=10), nullable=True),
            sa.Column('fault_type', sa.String(length=50), nullable=False),
            sa.Column('severity', sa.String(length=20), nullable=False, server_default='warning'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='detected'),
            sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
            sa.Column('rectified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolution', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['device_id'], ['devices.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_faults_id'), 'faults', ['id'], unique=False)
        op.create_index(op.f('ix_faults_device_id'), 'faults', ['device_id'], unique=False)
        op.create_index(op.f('ix_faults_status'), 'faults', ['status'], unique=False)
        op.create_index(op.f('ix_faults_detected_at'), 'faults', ['detected_at'], unique=False)

    _ensure_table(
        bind,
        'faults',
        _create_faults,
        required_columns=[
            sa.Column('device_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('phase', sa.String(length=10), nullable=True),
            sa.Column('fault_type', sa.String(length=50), nullable=False, server_default=''),
            sa.Column('severity', sa.String(length=20), nullable=False, server_default='warning'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='detected'),
            sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
            sa.Column('rectified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolution', sa.Text(), nullable=True),
        ],
        required_indexes=[
            ('ix_faults_id', ['id'], False),
            ('ix_faults_device_id', ['device_id'], False),
            ('ix_faults_status', ['status'], False),
            ('ix_faults_detected_at', ['detected_at'], False),
        ]
    )

    # 8. users (initial baseline schema)
    def _create_users():
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('username', sa.String(length=80), nullable=False),
            sa.Column('password_hash', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=30), nullable=False, server_default='operator'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    _ensure_table(
        bind,
        'users',
        _create_users,
        required_columns=[
            sa.Column('username', sa.String(length=80), nullable=False, server_default=''),
            sa.Column('password_hash', sa.String(length=255), nullable=False, server_default=''),
            sa.Column('role', sa.String(length=30), nullable=False, server_default='operator'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        ],
        required_indexes=[
            ('ix_users_id', ['id'], False),
            ('ix_users_username', ['username'], True),
        ]
    )

    # 9. notifications
    def _create_notifications():
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('fault_id', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(length=150), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(length=20), nullable=False, server_default='warning'),
            sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['fault_id'], ['faults.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
        op.create_index(op.f('ix_notifications_fault_id'), 'notifications', ['fault_id'], unique=False)
        op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)

    _ensure_table(
        bind,
        'notifications',
        _create_notifications,
        required_columns=[
            sa.Column('fault_id', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(length=150), nullable=False, server_default=''),
            sa.Column('message', sa.Text(), nullable=False, server_default=''),
            sa.Column('severity', sa.String(length=20), nullable=False, server_default='warning'),
            sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        ],
        required_indexes=[
            ('ix_notifications_id', ['id'], False),
            ('ix_notifications_fault_id', ['fault_id'], False),
            ('ix_notifications_created_at', ['created_at'], False),
        ]
    )

    # 10. work_orders
    def _create_work_orders():
        op.create_table(
            'work_orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('fault_id', sa.Integer(), nullable=False),
            sa.Column('assigned_to', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='assigned'),
            sa.Column('diagnosis', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('restored_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.String(length=100), nullable=True),
            sa.ForeignKeyConstraint(['fault_id'], ['faults.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_work_orders_id'), 'work_orders', ['id'], unique=False)
        op.create_index(op.f('ix_work_orders_fault_id'), 'work_orders', ['fault_id'], unique=False)
        op.create_index(op.f('ix_work_orders_status'), 'work_orders', ['status'], unique=False)

    _ensure_table(
        bind,
        'work_orders',
        _create_work_orders,
        required_columns=[
            sa.Column('fault_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('assigned_to', sa.String(length=100), nullable=False, server_default=''),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='assigned'),
            sa.Column('diagnosis', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('restored_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.String(length=100), nullable=True),
        ],
        required_indexes=[
            ('ix_work_orders_id', ['id'], False),
            ('ix_work_orders_fault_id', ['fault_id'], False),
            ('ix_work_orders_status', ['status'], False),
        ]
    )

    # 11. work_attempts
    def _create_work_attempts():
        op.create_table(
            'work_attempts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('work_order_id', sa.Integer(), nullable=False),
            sa.Column('note', sa.Text(), nullable=False),
            sa.Column('created_by', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_work_attempts_id'), 'work_attempts', ['id'], unique=False)
        op.create_index(op.f('ix_work_attempts_work_order_id'), 'work_attempts', ['work_order_id'], unique=False)

    _ensure_table(
        bind,
        'work_attempts',
        _create_work_attempts,
        required_columns=[
            sa.Column('work_order_id', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('note', sa.Text(), nullable=False, server_default=''),
            sa.Column('created_by', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        ],
        required_indexes=[
            ('ix_work_attempts_id', ['id'], False),
            ('ix_work_attempts_work_order_id', ['work_order_id'], False),
        ]
    )

    # 12. audit_logs
    def _create_audit_logs():
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('actor', sa.String(length=100), nullable=False),
            sa.Column('action', sa.String(length=80), nullable=False),
            sa.Column('entity_type', sa.String(length=50), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=True),
            sa.Column('detail', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
        op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
        op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)

    _ensure_table(
        bind,
        'audit_logs',
        _create_audit_logs,
        required_columns=[
            sa.Column('actor', sa.String(length=100), nullable=False, server_default=''),
            sa.Column('action', sa.String(length=80), nullable=False, server_default=''),
            sa.Column('entity_type', sa.String(length=50), nullable=False, server_default=''),
            sa.Column('entity_id', sa.Integer(), nullable=True),
            sa.Column('detail', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        ],
        required_indexes=[
            ('ix_audit_logs_id', ['id'], False),
            ('ix_audit_logs_action', ['action'], False),
            ('ix_audit_logs_created_at', ['created_at'], False),
        ]
    )


def downgrade() -> None:
    """Downgrade schema in reverse topological order."""
    bind = op.get_bind()

    tables = [
        ('audit_logs', ['ix_audit_logs_created_at', 'ix_audit_logs_action', 'ix_audit_logs_id']),
        ('work_attempts', ['ix_work_attempts_work_order_id', 'ix_work_attempts_id']),
        ('work_orders', ['ix_work_orders_status', 'ix_work_orders_fault_id', 'ix_work_orders_id']),
        ('notifications', ['ix_notifications_created_at', 'ix_notifications_fault_id', 'ix_notifications_id']),
        ('users', ['ix_users_username', 'ix_users_id']),
        ('faults', ['ix_faults_detected_at', 'ix_faults_status', 'ix_faults_device_id', 'ix_faults_id']),
        ('relays', ['ix_relays_device_id', 'ix_relays_id']),
        ('telemetry', ['ix_telemetry_received_at', 'ix_telemetry_sampled_at', 'ix_telemetry_device_id', 'ix_telemetry_id']),
        ('devices', ['ix_devices_floor_id', 'ix_devices_device_id', 'ix_devices_id']),
        ('floors', ['ix_floors_block_id', 'ix_floors_id']),
        ('blocks', ['ix_blocks_college_id', 'ix_blocks_id']),
        ('colleges', ['ix_colleges_id']),
    ]

    for table_name, indexes in tables:
        if _table_exists(bind, table_name):
            for idx_name in indexes:
                if _index_exists(bind, table_name, idx_name):
                    op.drop_index(op.f(idx_name), table_name=table_name)
            op.drop_table(table_name)
