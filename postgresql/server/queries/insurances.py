from typing import Optional
from server.pool import get_pool

# 🔍 Get insurance acceptance status by name
async def get_insurance_details(name: str) -> Optional[bool]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT accepted FROM insurance_details WHERE name = $1 LIMIT 1',
            name
        )
        return row["accepted"] if row else None
