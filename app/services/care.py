from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CareLog, Plant, Property, Room
from app.db.repositories import care as care_repo
from app.db.repositories import plants as plants_repo


async def mark_done(
    session: AsyncSession,
    plant_id: int,
    user_id: int,
    care_type_code: str = "watering",
) -> tuple[Plant, Room, Property] | None:
    """Отметить уход: запись в журнал + сдвиг следующего срока.

    Возвращает (растение, комната, property) для текста подтверждения,
    или None, если растение не найдено.
    """
    location = await plants_repo.get_plant_location(session, plant_id)
    if location is None:
        return None

    care_type = await care_repo.get_care_type(session, care_type_code)
    if care_type is None:
        return None
    now = datetime.now(timezone.utc)

    session.add(
        CareLog(
            plant_id=plant_id,
            user_id=user_id,
            care_type_id=care_type.id,
            done_at=now,
        )
    )

    schedule = await care_repo.get_schedule(session, plant_id, care_type.id)
    if schedule is not None:
        schedule.last_done_at = now
        schedule.next_due_at = now + timedelta(days=schedule.interval_days)
        schedule.last_reminded_at = None

    await session.commit()
    return location
