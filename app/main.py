from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes.health import router as health_router
from app.routes.index import router as index_router
from app.routes.upload import router as upload_router
from app.routes.validation import router as validation_router
from app.routes.history import router as history_router
from app.routes.suppliers import router as suppliers_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.jobs.scheduler import init_scheduler, shutdown_scheduler
    init_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Ledgerly", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(health_router)
app.include_router(index_router)
app.include_router(upload_router)
app.include_router(validation_router)
app.include_router(history_router)
app.include_router(suppliers_router)
