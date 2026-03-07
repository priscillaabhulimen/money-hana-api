from fastapi import FastAPI
import os
from pathlib import Path
from psycopg2 import pool
import time
from psycopg2.extras import DictCursor
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager


ROOT_DIR = Path(__file__).resolve().parents[1]
# Load local env vars when running directly with Uvicorn.
load_dotenv(ROOT_DIR / ".env")

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

DB_HOST = os.getenv("DB_HOST", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = int(os.getenv("DB_PORT", "5430"))
# Retry knobs help when API starts before Postgres is ready.
DB_CONNECT_RETRIES = int(os.getenv("DB_CONNECT_RETRIES", "10"))
DB_RETRY_DELAY_SECONDS = float(os.getenv("DB_RETRY_DELAY_SECONDS", "2"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create one process-level pool at startup and close it on shutdown.
    db_pool = None
    last_error = None

    for attempt in range(1, DB_CONNECT_RETRIES + 1):
        try:
            db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
                cursor_factory=DictCursor,
            )
            break
        except Exception as err:
            last_error = err
            print(f"Database connection attempt {attempt}/{DB_CONNECT_RETRIES} failed: {err}")
            if attempt < DB_CONNECT_RETRIES:
                time.sleep(DB_RETRY_DELAY_SECONDS)

    if db_pool is None:
        raise RuntimeError(f"Unable to connect to database after {DB_CONNECT_RETRIES} attempts: {last_error}")

    # Store pool on app state so request handlers can borrow connections.
    app.state.db_pool = db_pool

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
    conn = None
    try:
        # Borrow a connection for this request and return it in finally.
        conn = app.state.db_pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    finally:
        if conn is not None:
            app.state.db_pool.putconn(conn)
    