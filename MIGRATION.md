# Database Migrations Guide (Alembic)

This guide explains how to set up and run schema migrations for `money-hana-api`.

It is written for your current stack:
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL (`asyncpg` in app runtime)
- Project models in `app/models/`
- Base metadata from `app/base.py`

## 1. Why Migrations Matter

Migrations let you version and safely evolve your database schema.

Use migrations for changes like:
- creating/dropping tables
- adding/removing columns
- indexes and unique constraints
- check constraints (for example `amount > 0`)
- renames and data backfills

## 2. Prerequisites

1. Activate virtual environment.
2. Ensure dependencies are installed.
3. Ensure `.env` contains a valid `DATABASE_URL`.
4. Ensure your database is reachable.

Install Alembic if needed:

```bash
pip install alembic
```

If you want this tracked in dependencies, add `alembic` to `requirements.txt`.

## 3. Initialize Alembic (One-Time)

Run from project root:

```bash
alembic init alembic
```

This creates:
- `alembic.ini`
- `alembic/`
- `alembic/env.py`
- `alembic/versions/`

## 4. Configure Alembic for This Project

### 4.1 Update `alembic.ini`

Set your database URL in one of these ways:

1. Directly set `sqlalchemy.url` in `alembic.ini`.
2. Prefer loading from environment in `alembic/env.py` (recommended).

Recommended approach: keep `alembic.ini` minimal and load `DATABASE_URL` from `.env` inside `env.py`.

### 4.2 Update `alembic/env.py`

Set Alembic metadata and DB URL wiring.

Key points:
1. Import your SQLAlchemy metadata (`Base.metadata`).
2. Import all model modules before `target_metadata` so tables/constraints are registered.
3. Load `.env` and set `sqlalchemy.url` from `DATABASE_URL`.
4. Use a sync driver URL for Alembic connection if your app URL is async.

Example pattern:

```python
from logging.config import fileConfig
import os
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

from app.base import Base

# Import models so metadata includes all tables
from app.models.users import User  # noqa: F401
from app.models.transactions import Transaction  # noqa: F401
from app.models.goals import Goal  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

# Alembic uses synchronous SQLAlchemy engine.
# Convert asyncpg URL to psycopg URL for migrations.
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")
config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Notes:
- For the sync driver above, install one of:
- `psycopg[binary]` (recommended modern driver)
- `psycopg2-binary` (older common option; use `postgresql+psycopg2://` URL format)

## 5. Daily Migration Workflow

### 5.1 Generate migration after model changes

```bash
alembic revision --autogenerate -m "describe change"
```

### 5.2 Review generated migration file

Always review under `alembic/versions/` before applying.

Check for:
- correct table/column names
- expected nullability and defaults
- expected index/constraint operations
- no accidental destructive operations

### 5.3 Apply migration

```bash
alembic upgrade head
```

### 5.4 Verify status

```bash
alembic current
alembic history --verbose
```

### 5.5 Roll back one revision (if needed)

```bash
alembic downgrade -1
```

## 6. Your Current Pending Schema Change

You added model-level check constraints:
- `ck_transactions_amount_positive` on `transactions.amount > 0`
- `ck_goals_monthly_limit_positive` on `goals.monthly_limit > 0`

Create migration:

```bash
alembic revision --autogenerate -m "add positive money check constraints"
```

Then confirm generated operations include equivalent `create_check_constraint(...)` calls.

## 7. Data Safety Before Adding CHECK Constraints

If invalid data already exists, constraint creation can fail.

Run checks before upgrading:

```sql
SELECT id, amount
FROM transactions
WHERE amount <= 0;
```

```sql
SELECT id, monthly_limit
FROM goals
WHERE monthly_limit <= 0;
```

Fix invalid rows first, then run:

```bash
alembic upgrade head
```

## 8. Example Manual Migration Snippet

If autogenerate misses constraints, edit migration manually:

```python
from alembic import op


def upgrade() -> None:
    op.create_check_constraint(
        "ck_transactions_amount_positive",
        "transactions",
        "amount > 0",
    )
    op.create_check_constraint(
        "ck_goals_monthly_limit_positive",
        "goals",
        "monthly_limit > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_goals_monthly_limit_positive", "goals", type_="check")
    op.drop_constraint("ck_transactions_amount_positive", "transactions", type_="check")
```

## 9. Team Conventions (Recommended)

1. One logical schema change per migration.
2. Use clear migration messages.
3. Review every autogenerated migration before applying.
4. Never edit old committed migrations in shared branches.
5. Add manual comments for non-obvious data migrations.
6. Run migration tests against a real Postgres instance in CI when possible.

## 10. Common Issues

### Problem: `No changes detected`

Cause:
- models were not imported in `alembic/env.py`

Fix:
- import all model modules before `target_metadata`

### Problem: Driver/module import errors in Alembic

Cause:
- async URL used with sync Alembic engine

Fix:
- convert `postgresql+asyncpg://` to sync URL in `env.py`
- install corresponding sync driver (`psycopg` or `psycopg2`)

### Problem: Constraint creation fails

Cause:
- existing invalid data violates new constraint

Fix:
- clean data first, then rerun `alembic upgrade head`

## 11. Quick Command Reference

```bash
# One-time
alembic init alembic

# Create migration
alembic revision --autogenerate -m "message"

# Apply all pending
alembic upgrade head

# Rollback one
alembic downgrade -1

# Show current revision
alembic current

# Show history
alembic history --verbose
```

## 12. Suggested Next Step

After adding Alembic to this repo, generate and inspect the first migration for your current models and new CHECK constraints before applying it to shared environments.
