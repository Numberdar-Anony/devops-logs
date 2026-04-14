import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./devops_logs.db"

import asyncio
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import engine
from app.db.init_db import init_db

async def main():
    print("Initializing database...")
    await init_db(engine)
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(main())
