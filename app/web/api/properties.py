from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import plants as plants_repo
from app.web.deps import Member, get_member, get_session

router = APIRouter()


class PropertyIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)


@router.post("/properties")
async def create_property(
    body: PropertyIn,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    prop = await plants_repo.create_property(
        session, member.family.id, body.name.strip()
    )
    return {"id": prop.id, "name": prop.name}


@router.delete("/properties/{property_id}")
async def delete_property(
    property_id: int,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    family_id = await plants_repo.property_family_id(session, property_id)
    if family_id != member.family.id:
        raise HTTPException(status_code=404, detail="property_not_found")

    await plants_repo.delete_property(session, property_id)
    return {"ok": True}
