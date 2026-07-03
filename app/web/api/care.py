from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import care as care_repo
from app.db.repositories import plants as plants_repo
from app.services import care as care_service
from app.web.deps import Member, get_member, get_session

router = APIRouter()


@router.post("/plants/{plant_id}/water")
async def water_plant(
    plant_id: int,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    return await mark_care(plant_id, "watering", member, session)


@router.post("/plants/{plant_id}/care/{care_code}")
async def mark_care(
    plant_id: int,
    care_code: str,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    family_id = await plants_repo.plant_family_id(session, plant_id)
    if family_id != member.family.id:
        raise HTTPException(status_code=404, detail="plant_not_found")

    result = await care_service.mark_done(session, plant_id, member.user.id, care_code)
    if result is None:
        raise HTTPException(status_code=404, detail="care_type_not_found")
    return {"ok": True}


@router.get("/logs")
async def get_logs(
    limit: int = 30,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await care_repo.recent_logs(session, member.family.id, limit=min(limit, 100))
    return {
        "logs": [
            {
                "user": user.first_name,
                "plant": plant.name,
                "room": room.name,
                "property": prop.name,
                "care_type": care_type.name,
                "care_code": care_type.code,
                "at": log.done_at.isoformat(),
            }
            for log, user, plant, room, prop, care_type in rows
        ]
    }
