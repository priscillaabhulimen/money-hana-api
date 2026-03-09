# Setup Guide

Use this guide for first-time local setup.

## 1. Prerequisites

- Python 3.12+
- PostgreSQL database accessible from your machine

Optional but recommended in VS Code:

- `Python` extension (Microsoft)
- `Pylance` extension (Microsoft)

Check Python:

```bash
python3 --version
```

## 2. Create Virtual Environment

From the project root:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

## 3. Install Project Dependencies

Install pinned dependencies:

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a local env file:

```bash
cp .env.example .env
```

Set at least the following values in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>:<port>/<database-name>
AUTH_SECRET_KEY=<your-secret-key>
ALLOWED_ORIGINS=http://localhost:3000
RESEND_API_KEY=<your-resend-api-key>
EMAIL_FROM=<verified-sender-email>
```

Optional value for SQL query logging:

```env
DEBUG_SQL=true
```

If your password contains reserved URL characters (for example `@`), URL-encode them.

## 5. Database Schema

This repository does not currently include Alembic migration files.

On startup, the app currently auto-creates schema tables using `Base.metadata.create_all(...)`.

The expected tables are:

- `users`
- `transactions`
- `goals`

See `MIGRATION.md` for the migration workflow and recommended move to versioned migrations.

## 6. Run the API

```bash
uvicorn app.main:app --reload
```

Useful endpoints:

- `http://127.0.0.1:8000/docs`
- `GET /health` (includes a database connectivity check)