import asyncio
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.handlers import care, start
from app.bot.middlewares import DbSessionMiddleware
from app.config import settings
from app.scheduler.jobs import send_due_reminders
from app.web.app import create_app

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(start.router)
    dp.include_router(care.router)

    # Планировщик напоминаний — каждые 30 минут
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_due_reminders, "interval", minutes=30, args=[bot])
    scheduler.start()

    # Веб-сервер Mini App + бот (long polling) в одном event loop
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(bot),
            host="0.0.0.0",
            port=settings.port,
            log_level="info",
        )
    )

    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(
        dp.start_polling(bot),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
