import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.bot.keyboards import water_kb
from app.db.base import session_factory
from app.services.reminders import collect_due_reminders

logger = logging.getLogger(__name__)


async def send_due_reminders(bot: Bot) -> None:
    """Периодическая задача: найти просроченные расписания
    и разослать напоминания всем членам семьи."""
    async with session_factory() as session:
        reminders = await collect_due_reminders(session)

        for schedule, text, plant_id, member_ids in reminders:
            delivered = False
            for user_id in member_ids:
                try:
                    await bot.send_message(
                        user_id, text, reply_markup=water_kb(plant_id)
                    )
                    delivered = True
                except TelegramAPIError as e:
                    # Пользователь мог заблокировать бота — не роняем рассылку
                    logger.warning("Не доставлено user_id=%s: %s", user_id, e)

            if delivered:
                schedule.last_reminded_at = datetime.now(timezone.utc)

        await session.commit()
