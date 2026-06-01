import asyncio
import sys

from app.core.database import SessionLocal
from sqlalchemy import text


async def check() -> None:
    async with SessionLocal() as db:
        await db.execute(text("SELECT 1"))


if __name__ == "__main__":
    try:
        asyncio.run(check())
        sys.exit(0)
    except Exception:
        sys.exit(1)
