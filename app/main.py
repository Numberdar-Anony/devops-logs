import uvicorn
from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import engine

app = FastAPI(title=settings.app_name)
app.include_router(router)


@app.on_event("startup")
async def startup_event() -> None:
    await init_db(engine)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
