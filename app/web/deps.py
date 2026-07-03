from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import session_factory
from app.db.models import Family, User
from app.db.repositories import families as families_repo
from app.db.repositories import users as users_repo
from app.web.auth import validate_init_data


async def get_session() -> AsyncSession:
    async with session_factory() as session:
        yield session


@dataclass
class Member:
    user: User
    family: Family


async def get_member(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
) -> Member:
    """Аутентификация Mini App: initData → пользователь → его семья."""
    scheme, _, init_data = authorization.partition(" ")
    if scheme.lower() != "tma" or not init_data:
        raise HTTPException(status_code=401, detail="no_init_data")

    tg_user = validate_init_data(init_data)
    if tg_user is None:
        raise HTTPException(status_code=401, detail="bad_signature")

    user = await users_repo.get_or_create(
        session, tg_user["id"], tg_user.get("first_name", ""), tg_user.get("username")
    )
    family = await families_repo.get_user_family(session, user.id)
    if family is None:
        # Mini App покажет подсказку «создай семью в чате с ботом»
        raise HTTPException(status_code=403, detail="no_family")

    return Member(user=user, family=family)
