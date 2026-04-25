"""Alembic environment for Flask SQLAlchemy models."""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import create_app
from extensions import db

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

app = create_app()
with app.app_context():
    target_metadata = db.metadata


def get_database_url() -> str:
    """Resolve DB URL for multi-container setup with host `db`."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    db_user = os.getenv("DB_USER", "birdeye")
    db_password = os.getenv("DB_PASSWORD", "birdeye")
    db_name = os.getenv("DB_NAME", "birdeye_db")
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
