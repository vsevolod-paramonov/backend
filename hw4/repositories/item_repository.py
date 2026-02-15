from database import get_db_pool


async def get_item_by_item_id(item_id: int):
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT i.item_id, i.seller_id, i.name, i.description, i.category, i.images_qty,
                          u.is_verified_seller
                   FROM items i
                   JOIN users u ON i.seller_id = u.seller_id
                   WHERE i.item_id = $1""",
                item_id
            )
            if row:
                return {
                    "item_id": row["item_id"],
                    "seller_id": row["seller_id"],
                    "name": row["name"],
                    "description": row["description"],
                    "category": row["category"],
                    "images_qty": row["images_qty"],
                    "is_verified_seller": row["is_verified_seller"]
                }
            return None
    except Exception as e:
        raise Exception(f"Database error: {str(e)}")


async def create_item(item_id: int, seller_id: int, name: str, description: str, category: int, images_qty: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO items (item_id, seller_id, name, description, category, images_qty) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (item_id) DO NOTHING",
            item_id, seller_id, name, description, category, images_qty
        )