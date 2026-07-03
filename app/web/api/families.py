from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import care as care_repo
from app.db.repositories import plants as plants_repo
from app.web.deps import Member, get_member, get_session

router = APIRouter()


@router.get("/state")
async def get_state(
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    """Всё состояние семьи одним запросом: иерархия + сроки + кто поливал."""
    tree = await plants_repo.get_family_tree(session, member.family.id)
    latest = await care_repo.latest_log_by_plant(session, member.family.id)
    now = datetime.now(timezone.utc)

    def plant_dict(plant):
        care = []
        for schedule in plant.schedules:
            if not schedule.enabled:
                continue
            due = False
            due_in_days = None
            if schedule.next_due_at:
                delta = schedule.next_due_at - now
                due = schedule.next_due_at <= now
                due_in_days = 0 if due else delta.days
            care.append(
                {
                    "code": schedule.care_type.code,
                    "name": schedule.care_type.name,
                    "interval_days": schedule.interval_days,
                    "due": due,
                    "due_in_days": due_in_days,
                }
            )
        # Полив первым, остальное по алфавиту
        care.sort(key=lambda c: (c["code"] != "watering", c["code"]))

        last = latest.get(plant.id)
        return {
            "id": plant.id,
            "name": plant.name,
            "species": plant.species,
            "photo_file_id": plant.photo_file_id,
            "care": care,
            "last_care": (
                {"by": last[0].first_name, "at": last[1].isoformat(), "code": last[2]}
                if last
                else None
            ),
        }

    return {
        "user": {"id": member.user.id, "first_name": member.user.first_name},
        "family": {
            "id": member.family.id,
            "name": member.family.name,
            "invite_code": member.family.invite_code,
        },
        "properties": [
            {
                "id": prop.id,
                "name": prop.name,
                "rooms": [
                    {
                        "id": room.id,
                        "name": room.name,
                        "plants": [plant_dict(p) for p in room.plants],
                    }
                    for room in prop.rooms
                ],
            }
            for prop in tree
        ],
    }
