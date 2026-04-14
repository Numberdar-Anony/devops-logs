import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./devops_logs.db"

import asyncio
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.db_models import PersistedAnalysis

async def verify():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PersistedAnalysis).order_by(PersistedAnalysis.id.desc()).limit(1)
        )
        latest = result.scalars().first()

        if not latest:
            print("No analysis records found in database.")
            return

        print(f"--- Analysis ID: {latest.analysis_id} ---")
        print("Summary:")
        print(latest.summary)

        print("\nRoot Cause:")
        print(latest.root_cause)

        print("\nStructured Fix:")
        import json
        print(json.dumps(latest.structured_fix, indent=2))

if __name__ == "__main__":
    asyncio.run(verify())
