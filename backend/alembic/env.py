from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.db.database import Base

# Import all models so Alembic can detect them
from app.models import (
    College,
    Block,
    Floor,
    Device,
    Telemetry,
    Relay,
    Fault,
    User,
    Notification,
    WorkOrder,
    WorkAttempt,
    AuditLog,
)



config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    x_args = context.get_x_argument(as_dictionary=True)
    db_url = x_args.get("db_url") or x_args.get("url") or config.get_main_option("sqlalchemy.url")
    if not db_url:
        db_url = settings.DATABASE_URL

    configuration = {
        "sqlalchemy.url": db_url,
    }

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()