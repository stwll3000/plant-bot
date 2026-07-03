from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import plants as plants_repo
from app.web.auth import validate_init_data
from app.web.deps import Member, get_member, get_session

router = APIRouter()


class PlantIn(BaseModel):
    room_id: int
    name: str = Field(min_length=1, max_length=128)
    species: str | None = Field(default=None, max_length=128)
    interval_days: int = Field(ge=1, le=365)


@router.post("/plants")
async def create_plant(
    body: PlantIn,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    family_id = await plants_repo.room_family_id(session, body.room_id)
    if family_id != member.family.id:
        raise HTTPException(status_code=404, detail="room_not_found")

    plant = await plants_repo.create_plant(
        session,
        body.room_id,
        body.name.strip(),
        (body.species or "").strip() or None,
        body.interval_days,
    )
    return {"id": plant.id, "name": plant.name}


@router.get("/photo/{file_id}")
async def get_photo(
    file_id: str,
    request: Request,
    a: str = Query(default=""),
):
    """Отдаёт фото растения по telegram file_id.

    <img> не умеет слать заголовки, поэтому initData приходит
    query-параметром `a`. Скачиваем файл через бота, токен наружу не утекает.
    """
    if validate_init_data(a) is None:
        raise HTTPException(status_code=401, detail="bad_signature")

    bot = request.app.state.bot
    try:
        file = await bot.get_file(file_id)
        buffer = BytesIO()
        await bot.download_file(file.file_path, destination=buffer)
    except Exception:
        raise HTTPException(status_code=404, detail="file_not_found")

    return Response(content=buffer.getvalue(), media_type="image/jpeg")
