from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_or_create(
    session: AsyncSession, user_id: int, first_name: str, username: str | None
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, first_name=first_name or "—", username=username)
        session.add(user)
        await session.commit()
    elif user.first_name != first_name or user.username != username:
        user.first_name = first_name or user.first_name
        user.username = username
        await session.commit()
    return user
