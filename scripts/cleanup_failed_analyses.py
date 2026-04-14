import asyncio
import sys
import os

# Add the project root to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, or_
from app.db.session import AsyncSessionLocal
from app.models.db_models import AnalysisResult, PersistedAnalysis

async def cleanup():
    failure_patterns = [
        "%OpenRouter call failed%",
        "%Missing Authentication header%",
        "%LLM call failed%",
    ]

    async with AsyncSessionLocal() as session:
        # Check AnalysisResult (legacy)
        legacy_query = delete(AnalysisResult).where(
            or_(
                *[AnalysisResult.root_cause.ilike(p) for p in failure_patterns],
                *[AnalysisResult.fix.ilike(p) for p in failure_patterns]
            )
        )
        
        # Check PersistedAnalysis (new)
        persisted_query = delete(PersistedAnalysis).where(
            or_(
                *[PersistedAnalysis.summary.ilike(p) for p in failure_patterns],
                *[PersistedAnalysis.root_cause.ilike(p) for p in failure_patterns],
                *[PersistedAnalysis.recommendation.ilike(p) for p in failure_patterns]
            )
        )

        # We can't easily get the count with a delete statement in SQLAlchemy async without 
        # doing a select first if we want exactly what the user asked (Print how many records were found)
        
        # Count legacy
        from sqlalchemy import select, func
        legacy_count_stmt = select(func.count()).select_from(AnalysisResult).where(
            or_(
                *[AnalysisResult.root_cause.ilike(p) for p in failure_patterns],
                *[AnalysisResult.fix.ilike(p) for p in failure_patterns]
            )
        )
        res = await session.execute(legacy_count_stmt)
        legacy_count = res.scalar()

        # Count persisted
        persisted_count_stmt = select(func.count()).select_from(PersistedAnalysis).where(
            or_(
                *[PersistedAnalysis.summary.ilike(p) for p in failure_patterns],
                *[PersistedAnalysis.root_cause.ilike(p) for p in failure_patterns],
                *[PersistedAnalysis.recommendation.ilike(p) for p in failure_patterns]
            )
        )
        res = await session.execute(persisted_count_stmt)
        persisted_count = res.scalar()

        total_found = legacy_count + persisted_count
        print(f"Found {total_found} failed analyses")

        if total_found > 0:
            await session.execute(legacy_query)
            await session.execute(persisted_query)
            await session.commit()
            print(f"Deleted {total_found} failed analyses")
        else:
            print("No failed analyses to delete")

if __name__ == "__main__":
    asyncio.run(cleanup())
