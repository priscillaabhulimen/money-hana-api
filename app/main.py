from fastapi import FastAPI
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import DictCursor
from pydantic import BaseModel
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

app = FastAPI()


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", ""),
        database=os.getenv("DB_NAME", ""),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        port=int(os.getenv("DB_PORT", "5430")),
        cursor_factory=DictCursor,
    )

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/items")
async def create_item(item: Item):
    return {"item": item}

@app.get("/health")
async def health_check():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}