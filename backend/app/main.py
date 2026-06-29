from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import settings
from app.logging_setup import setup_logging
from app.ws import register_ws

setup_logging()

app = FastAPI(
    title="draw-bitch",
    description="Реалтайм-игра «рисуй и угадывай»",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
register_ws(app)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "draw-bitch", "docs": "/docs"}
