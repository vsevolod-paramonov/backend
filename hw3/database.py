import asyncpg
import os
from typing import Optional

# Параметры подключения к БД
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", 'user')
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "moderationservices")

pool: Optional[asyncpg.Pool] = None


async def get_db_pool():
    global pool
    if pool is None or pool.is_closing():
        if pool is not None:
            try:
                await pool.close()
            except:
                pass
        pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
    return pool


async def close_db_pool():
    global pool
    if pool is not None:
        await pool.close()
        pool = None

