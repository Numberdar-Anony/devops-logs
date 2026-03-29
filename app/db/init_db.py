from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.base import Base
# Import models so metadata is populated before create_all
import app.models.db_models  # noqa: F401


async def init_db(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
