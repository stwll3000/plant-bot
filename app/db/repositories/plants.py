from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import CareType, Plant, PlantCareSchedule, Property, Room


async def create_property(
    session: AsyncSession, family_id: int, name: str
) -> Property:
    prop = Property(family_id=family_id, name=name)
    session.add(prop)
    await session.commit()
    return prop


async def create_room(session: AsyncSession, property_id: int, name: str) -> Room:
    room = Room(property_id=property_id, name=name)
    session.add(room)
    await session.commit()
    return room


async def create_plant(
    session: AsyncSession,
    room_id: int,
    name: str,
    species: str | None,
    interval_days: int,
    spraying_days: int | None = None,
) -> Plant:
    plant = Plant(room_id=room_id, name=name, species=species)
    session.add(plant)
    await session.flush()

    # Сразу заводим расписания; считаем, что уход выполнен сегодня
    await upsert_schedule(session, plant.id, "watering", interval_days, commit=False)
    if spraying_days:
        await upsert_schedule(session, plant.id, "spraying", spraying_days, commit=False)
    await session.commit()
    return plant


async def upsert_schedule(
    session: AsyncSession,
    plant_id: int,
    care_code: str,
    interval_days: int | None,
    commit: bool = True,
) -> None:
    """Создать/обновить расписание ухода. interval_days=None — выключить."""
    care_type = await session.scalar(
        select(CareType).where(CareType.code == care_code)
    )
    if care_type is None:
        return

    schedule = await session.scalar(
        select(PlantCareSchedule).where(
            PlantCareSchedule.plant_id == plant_id,
            PlantCareSchedule.care_type_id == care_type.id,
        )
    )
    now = datetime.now(timezone.utc)

    if interval_days is None:
        if schedule is not None:
            schedule.enabled = False
    elif schedule is not None:
        schedule.interval_days = interval_days
        schedule.enabled = True
        schedule.next_due_at = (schedule.last_done_at or now) + timedelta(
            days=interval_days
        )
    else:
        session.add(
            PlantCareSchedule(
                plant_id=plant_id,
                care_type_id=care_type.id,
                interval_days=interval_days,
                last_done_at=now,
                next_due_at=now + timedelta(days=interval_days),
            )
        )
    if commit:
        await session.commit()


async def get_family_tree(session: AsyncSession, family_id: int) -> list[Property]:
    """Вся иерархия семьи: property → rooms → plants → schedules."""
    stmt = (
        select(Property)
        .where(Property.family_id == family_id)
        .options(
            selectinload(Property.rooms)
            .selectinload(Room.plants)
            .selectinload(Plant.schedules)
            .selectinload(PlantCareSchedule.care_type)
        )
        .order_by(Property.id)
    )
    return list((await session.scalars(stmt)).all())


async def get_plant_location(
    session: AsyncSession, plant_id: int
) -> tuple[Plant, Room, Property] | None:
    stmt = (
        select(Plant, Room, Property)
        .join(Room, Plant.room_id == Room.id)
        .join(Property, Room.property_id == Property.id)
        .where(Plant.id == plant_id)
    )
    row = (await session.execute(stmt)).first()
    return tuple(row) if row else None


async def get_family_plants(session: AsyncSession, family_id: int) -> list[Plant]:
    stmt = (
        select(Plant)
        .join(Room, Plant.room_id == Room.id)
        .join(Property, Room.property_id == Property.id)
        .where(Property.family_id == family_id)
        .order_by(Plant.name)
    )
    return list((await session.scalars(stmt)).all())


async def plant_family_id(session: AsyncSession, plant_id: int) -> int | None:
    stmt = (
        select(Property.family_id)
        .join(Room, Room.property_id == Property.id)
        .join(Plant, Plant.room_id == Room.id)
        .where(Plant.id == plant_id)
    )
    return await session.scalar(stmt)


async def property_family_id(session: AsyncSession, property_id: int) -> int | None:
    return await session.scalar(
        select(Property.family_id).where(Property.id == property_id)
    )


async def room_family_id(session: AsyncSession, room_id: int) -> int | None:
    stmt = (
        select(Property.family_id)
        .join(Room, Room.property_id == Property.id)
        .where(Room.id == room_id)
    )
    return await session.scalar(stmt)


async def set_photo(session: AsyncSession, plant_id: int, file_id: str) -> None:
    plant = await session.get(Plant, plant_id)
    if plant is not None:
        plant.photo_file_id = file_id
        await session.commit()


async def get_plant(session: AsyncSession, plant_id: int) -> Plant | None:
    return await session.get(Plant, plant_id)


# Удаление — core-запросами: дочерние записи (комнаты, растения,
# расписания, журнал) подчищает сама БД через ondelete=CASCADE

async def delete_property(session: AsyncSession, property_id: int) -> None:
    await session.execute(delete(Property).where(Property.id == property_id))
    await session.commit()


async def delete_room(session: AsyncSession, room_id: int) -> None:
    await session.execute(delete(Room).where(Room.id == room_id))
    await session.commit()


async def delete_plant(session: AsyncSession, plant_id: int) -> None:
    await session.execute(delete(Plant).where(Plant.id == plant_id))
    await session.commit()
