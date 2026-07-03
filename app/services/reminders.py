from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import care as care_repo
from app.db.repositories import families as families_repo

CARE_EMOJI = {"watering": "💧"}


def reminder_text(care_type_name: str, care_type_code: str, plant, room, prop) -> str:
    emoji = CARE_EMOJI.get(care_type_code, "🪴")
    return (
        f"{emoji} Пора: <b>{care_type_name.lower()}</b> — "
        f"<b>{plant.name}</b>\n📍 {prop.name}, {room.name}"
    )


async def collect_due_reminders(session: AsyncSession):
    """Что пора сделать: [(schedule, текст, plant_id, family_member_ids)]."""
    now = datetime.now(timezone.utc)
    due = await care_repo.get_due_schedules(session, now)

    reminders = []
    members_cache: dict[int, list[int]] = {}
    for schedule, plant, room, prop, care_type in due:
        family_id = prop.family_id
        if family_id not in members_cache:
            members = await families_repo.get_members(session, family_id)
            members_cache[family_id] = [m.id for m in members]

        text = reminder_text(care_type.name, care_type.code, plant, room, prop)
        reminders.append((schedule, text, plant.id, members_cache[family_id]))

    return reminders
