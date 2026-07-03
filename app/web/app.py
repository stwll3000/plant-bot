from pathlib import Path

from aiogram import Bot
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.api import care, families, plants, properties, rooms

STATIC_DIR = Path(__file__).parent / "static"


def create_app(bot: Bot) -> FastAPI:
    app = FastAPI(title="Plant Tracker Mini App", docs_url=None, redoc_url=None)
    app.state.bot = bot

    for router in (families.router, properties.router, rooms.router,
                   plants.router, care.router):
        app.include_router(router, prefix="/api")

    # Статика Mini App — монтируем последней, чтобы не перехватывала /api
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
