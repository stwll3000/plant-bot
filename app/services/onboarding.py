from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Family
from app.db.repositories import families as families_repo


async def get_user_family(session: AsyncSession, user_id: int) -> Family | None:
    return await families_repo.get_user_family(session, user_id)


async def create_family(session: AsyncSession, user_id: int, name: str) -> Family:
    return await families_repo.create_with_owner(session, name.strip(), user_id)


async def join_family(
    session: AsyncSession, user_id: int, code: str
) -> Family | None:
    """Вступление по invite-коду. None — код не найден."""
    family = await families_repo.get_by_invite_code(session, code)
    if family is None:
        return None
    await families_repo.add_member(session, family.id, user_id)
    return family


def invite_link(bot_username: str, family: Family) -> str:
    return f"https://t.me/{bot_username}?start={family.invite_code}"
