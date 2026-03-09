# Installation Guide

Use this guide to recreate the project from a fresh machine or a clean checkout.

## 1. Install Python

- Install Python 3.12+
- Verify:

```bash
python3 --version
```

## 2. Create and Activate Virtual Environment

Run in the project root:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

## 3. Install All Dependencies

Install from `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 4. Create Environment Config

```bash
cp .env.example .env
```

Set your real database values in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>:<port>/<database-name>
AUTH_SECRET_KEY=<your-secret-key>
ALLOWED_ORIGINS=http://localhost:3000
```

Optional:

```env
DEBUG_SQL=true
```

## 5. Ensure Database Schema Exists

This repository currently has no committed Alembic migration directory.

The app currently creates schema tables automatically on startup using `Base.metadata.create_all(...)`.

Expected tables:

- `users`
- `transactions`
- `goals`

Migration setup details are in `MIGRATION.md`.

## 6. Start the API

```bash
uvicorn app.main:app --reload
```

Then verify:

- `http://127.0.0.1:8000/docs`
- `GET /health` returns `{"status": "ok"}`

## 7. Fast Rebuild Commands

If you need to recreate the environment later:

```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
