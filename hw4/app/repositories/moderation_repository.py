from database import get_db_pool
from datetime import datetime


async def create_moderation_task(item_id):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO moderation_results (item_id, status) VALUES ($1, 'pending') RETURNING id",
            item_id
        )
        return row["id"]


async def get_moderation_task(task_id):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, item_id, status, is_violation, probability, error_message, created_at, processed_at "
            "FROM moderation_results WHERE id = $1",
            task_id
        )
        return dict(row) if row else None


async def get_pending_task_by_item_id(item_id):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM moderation_results WHERE item_id = $1 AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
            item_id
        )
        return row["id"] if row else None


async def update_moderation_result(task_id, status, is_violation=None, probability=None, error_message=None):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if status == "completed":
            await conn.execute(
                "UPDATE moderation_results SET status = $1, is_violation = $2, probability = $3, processed_at = $4 WHERE id = $5",
                status, is_violation, probability, datetime.utcnow(), task_id
            )
        else:  # failed
            await conn.execute(
                "UPDATE moderation_results SET status = $1, error_message = $2, processed_at = $3 WHERE id = $4",
                status, error_message, datetime.utcnow(), task_id
            )

