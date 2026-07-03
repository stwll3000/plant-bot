from fastapi import APIRouter, Depends
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
