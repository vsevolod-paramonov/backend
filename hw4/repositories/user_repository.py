from database import get_db_pool


async def get_user_by_seller_id(seller_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT seller_id, is_verified_seller FROM users WHERE seller_id = $1",
            seller_id
        )
        if row:
            return {
                "seller_id": row["seller_id"],
                "is_verified_seller": row["is_verified_seller"]
            }
        return None


async def create_user(seller_id: int, is_verified_seller: bool):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (seller_id, is_verified_seller) VALUES ($1, $2) ON CONFLICT (seller_id) DO NOTHING",
            seller_id, is_verified_seller
        )

