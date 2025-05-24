from typing import List
from datetime import datetime
from server.pool import get_pool

# 🔍 Get available appointment slots within a time range
async def get_available_time_slots(start_time: datetime, end_time: datetime) -> List[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, start_time
            FROM appt_slots
            WHERE is_available = TRUE
              AND start_time >= $1
              AND start_time <= $2
            ORDER BY start_time ASC
            """,
            start_time,
            end_time
        )
        return [dict(row) for row in rows]
