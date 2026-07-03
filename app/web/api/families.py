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
        watering = next(
            (s for s in plant.schedules if s.care_type.code == "watering"), None
        )
        last = latest.get(plant.id)
        due_in_days = None
        due = False
        if watering and watering.next_due_at:
            delta = watering.next_due_at - now
            due_in_days = delta.days if delta.total_seconds() > 0 else 0
            due = watering.next_due_at <= now
        return {
            "id": plant.id,
            "name": plant.name,
            "species": plant.species,
            "photo_file_id": plant.photo_file_id,
            "interval_days": watering.interval_days if watering else None,
            "next_due_at": (
                watering.next_due_at.isoformat()
                if watering and watering.next_due_at
                else None
            ),
            "due": due,
            "due_in_days": due_in_days,
            "last_care": (
                {"by": last[0].first_name, "at": last[1].isoformat()}
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
