from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CareLog,
    CareType,
    Plant,
    PlantCareSchedule,
    Property,
    Room,
    User,
)


async def get_care_type(session: AsyncSession, code: str) -> CareType | None:
    return await session.scalar(select(CareType).where(CareType.code == code))


async def get_schedule(
    session: AsyncSession, plant_id: int, care_type_id: int
) -> PlantCareSchedule | None:
    return await session.scalar(
        select(PlantCareSchedule).where(
            PlantCareSchedule.plant_id == plant_id,
            PlantCareSchedule.care_type_id == care_type_id,
        )
    )


async def latest_log_by_plant(
    session: AsyncSession, family_id: int
) -> dict[int, tuple[User, datetime]]:
    """Последняя запись ухода по каждому растению семьи (DISTINCT ON)."""
    stmt = (
        select(CareLog, User)
        .join(User, CareLog.user_id == User.id)
        .join(Plant, CareLog.plant_id == Plant.id)
        .join(Room, Plant.room_id == Room.id)
        .join(Property, Room.property_id == Property.id)
        .where(Property.family_id == family_id)
        .distinct(CareLog.plant_id)
        .order_by(CareLog.plant_id, CareLog.done_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    return {log.plant_id: (user, log.done_at) for log, user in rows}


async def recent_logs(session: AsyncSession, family_id: int, limit: int = 30):
    """Общий журнал семьи: кто, что, где и когда."""
    stmt = (
        select(CareLog, User, Plant, Room, Property, CareType)
        .join(User, CareLog.user_id == User.id)
        .join(Plant, CareLog.plant_id == Plant.id)
        .join(Room, Plant.room_id == Room.id)
        .join(Property, Room.property_id == Property.id)
        .join(CareType, CareLog.care_type_id == CareType.id)
        .where(Property.family_id == family_id)
        .order_by(CareLog.done_at.desc())
        .limit(limit)
    )
    return (await session.execute(stmt)).all()


async def get_due_schedules(session: AsyncSession, now: datetime):
    """Расписания, по которым пора напомнить.

    Повторное напоминание по тому же растению — не чаще раза в 23 часа.
    """
    remind_threshold = now - timedelta(hours=23)
    stmt = (
        select(PlantCareSchedule, Plant, Room, Property, CareType)
        .join(Plant, PlantCareSchedule.plant_id == Plant.id)
        .join(Room, Plant.room_id == Room.id)
        .join(Property, Room.property_id == Property.id)
        .join(CareType, PlantCareSchedule.care_type_id == CareType.id)
        .where(
            PlantCareSchedule.enabled.is_(True),
            PlantCareSchedule.next_due_at <= now,
            or_(
                PlantCareSchedule.last_reminded_at.is_(None),
                PlantCareSchedule.last_reminded_at <= remind_threshold,
            ),
        )
    )
    return (await session.execute(stmt)).all()
