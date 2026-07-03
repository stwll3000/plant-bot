import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Family, Membership, User

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _generate_code(length: int = 8) -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


async def get_user_family(session: AsyncSession, user_id: int) -> Family | None:
    stmt = (
        select(Family)
        .join(Membership, Membership.family_id == Family.id)
        .where(Membership.user_id == user_id)
    )
    return await session.scalar(stmt)


async def get_by_invite_code(session: AsyncSession, code: str) -> Family | None:
    stmt = select(Family).where(Family.invite_code == code.strip().upper())
    return await session.scalar(stmt)


async def create_with_owner(
    session: AsyncSession, name: str, owner_id: int
) -> Family:
    # Подбираем свободный invite-код (коллизии крайне маловероятны)
    code = _generate_code()
    while await get_by_invite_code(session, code) is not None:
        code = _generate_code()

    family = Family(name=name, invite_code=code)
    session.add(family)
    await session.flush()
    session.add(Membership(user_id=owner_id, family_id=family.id, role="owner"))
    await session.commit()
    return family


async def add_member(session: AsyncSession, family_id: int, user_id: int) -> None:
    exists = await session.scalar(
        select(Membership).where(
            Membership.family_id == family_id, Membership.user_id == user_id
        )
    )
    if exists is None:
        session.add(Membership(user_id=user_id, family_id=family_id, role="member"))
        await session.commit()


async def get_members(session: AsyncSession, family_id: int) -> list[User]:
    stmt = (
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.family_id == family_id)
    )
    return list((await session.scalars(stmt)).all())
