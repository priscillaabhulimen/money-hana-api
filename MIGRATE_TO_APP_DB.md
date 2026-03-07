# Migrate DB Logic To `app/db.py`

This guide moves database setup and health-check query helpers out of `app/main.py` and into `app/db.py`.

## Why migrate

- Keeps `app/main.py` focused on routes.
- Centralizes database configuration and lifecycle logic.
- Makes DB code easier to test and reuse.

## Target structure

- `app/main.py`: FastAPI app + route handlers.
- `app/db.py`: env loading, pool creation, retry policy, connection helpers.

## Step 1: Create `app/db.py`

```python
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from psycopg2 import pool
from psycopg2.extras import DictCursor

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = int(os.getenv("DB_PORT", "5430"))
DB_CONNECT_RETRIES = int(os.getenv("DB_CONNECT_RETRIES", "10"))
DB_RETRY_DELAY_SECONDS = float(os.getenv("DB_RETRY_DELAY_SECONDS", "2"))


def create_pool() -> pool.SimpleConnectionPool:
    last_error = None

    for attempt in range(1, DB_CONNECT_RETRIES + 1):
        try:
            return pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
                cursor_factory=DictCursor,
            )
        except Exception as err:
            last_error = err
            print(f"Database connection attempt {attempt}/{DB_CONNECT_RETRIES} failed: {err}")
            if attempt < DB_CONNECT_RETRIES:
                time.sleep(DB_RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Unable to connect to database after {DB_CONNECT_RETRIES} attempts: {last_error}"
    )


def check_db(pool_obj: pool.SimpleConnectionPool) -> None:
    conn = None
    try:
        conn = pool_obj.getconn()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    finally:
        if conn is not None:
            pool_obj.putconn(conn)
```

## Step 2: Update `app/main.py`

Replace DB setup code with imports from `app/db.py`.

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app.db import check_db, create_pool


class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = create_pool()
    try:
        yield
    finally:
        app.state.db_pool.closeall()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/items")
async def create_item(item: Item):
    return {"item": item}


@app.get("/health")
async def health_check():
    try:
        check_db(app.state.db_pool)
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Step 3: Keep env variables in `.env`

```env
DB_HOST=localhost
DB_PORT=5430
DB_NAME=moneyhana_dev
DB_USER=postgres
DB_PASSWORD=your_password
DB_CONNECT_RETRIES=10
DB_RETRY_DELAY_SECONDS=2
```

## Step 4: Restart and verify

1. Restart the API server.
2. Call `GET /health`.
3. Confirm response is `{"status": "healthy"}`.

## Optional next improvements

- Replace `print` calls with `logging`.
- Return a connection dependency via FastAPI `Depends` for query routes.
- Move credentials to secret management for production.
