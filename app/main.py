from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: init APScheduler here (step 8)
    yield
    # TODO: shutdown scheduler


app = FastAPI(title="Ledgerly", lifespan=lifespan)
app.include_router(health_router)
