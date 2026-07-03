from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import plants as plants_repo
from app.web.deps import Member, get_member, get_session

router = APIRouter()


class RoomIn(BaseModel):
    property_id: int
    name: str = Field(min_length=1, max_length=128)


@router.post("/rooms")
async def create_room(
    body: RoomIn,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    # Проверяем, что property принадлежит семье пользователя
    family_id = await plants_repo.property_family_id(session, body.property_id)
    if family_id != member.family.id:
        raise HTTPException(status_code=404, detail="property_not_found")

    room = await plants_repo.create_room(session, body.property_id, body.name.strip())
    return {"id": room.id, "name": room.name}
