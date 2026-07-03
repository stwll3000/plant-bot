from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db.base import session_factory
from app.db.repositories import users as users_repo


class DbSessionMiddleware(BaseMiddleware):
    """Открывает DB-сессию на каждый апдейт и гарантирует,
    что пользователь есть в таблице users."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_factory() as session:
            data["session"] = session
            tg_user = data.get("event_from_user")
            if tg_user is not None and not tg_user.is_bot:
                await users_repo.get_or_create(
                    session, tg_user.id, tg_user.first_name, tg_user.username
                )
            return await handler(event, data)
