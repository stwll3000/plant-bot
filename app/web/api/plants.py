from io import BytesIO

from aiogram.types import BufferedInputFile
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import plants as plants_repo
from app.web.auth import validate_init_data
from app.web.deps import Member, get_member, get_session

MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 МБ — лимит Telegram на sendPhoto

router = APIRouter()


class PlantIn(BaseModel):
    room_id: int
    name: str = Field(min_length=1, max_length=128)
    species: str | None = Field(default=None, max_length=128)
    interval_days: int = Field(ge=1, le=365)
    spraying_days: int | None = Field(default=None, ge=1, le=365)


class SchedulesIn(BaseModel):
    watering_days: int = Field(ge=1, le=365)
    spraying_days: int | None = Field(default=None, ge=1, le=365)


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
        body.spraying_days,
    )
    return {"id": plant.id, "name": plant.name}


@router.put("/plants/{plant_id}/schedules")
async def update_schedules(
    plant_id: int,
    body: SchedulesIn,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    """Интервалы ухода: полив обязателен, опрыскивание опционально
    (None — выключить)."""
    family_id = await plants_repo.plant_family_id(session, plant_id)
    if family_id != member.family.id:
        raise HTTPException(status_code=404, detail="plant_not_found")

    await plants_repo.upsert_schedule(
        session, plant_id, "watering", body.watering_days, commit=False
    )
    await plants_repo.upsert_schedule(
        session, plant_id, "spraying", body.spraying_days, commit=False
    )
    await session.commit()
    return {"ok": True}


@router.delete("/plants/{plant_id}")
async def delete_plant(
    plant_id: int,
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    family_id = await plants_repo.plant_family_id(session, plant_id)
    if family_id != member.family.id:
        raise HTTPException(status_code=404, detail="plant_not_found")

    await plants_repo.delete_plant(session, plant_id)
    return {"ok": True}


@router.post("/plants/{plant_id}/photo")
async def upload_photo(
    plant_id: int,
    request: Request,
    file: UploadFile = File(...),
    member: Member = Depends(get_member),
    session: AsyncSession = Depends(get_session),
):
    """Фото из Mini App: файл уходит ботом в чат пользователя —
    так мы получаем telegram file_id и не держим своё хранилище."""
    family_id = await plants_repo.plant_family_id(session, plant_id)
    if family_id != member.family.id:
        raise HTTPException(status_code=404, detail="plant_not_found")

    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=415, detail="not_an_image")

    data = await file.read()
    if len(data) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=413, detail="file_too_large")

    plant = await plants_repo.get_plant(session, plant_id)
    bot = request.app.state.bot
    message = await bot.send_photo(
        member.user.id,
        BufferedInputFile(data, filename="plant.jpg"),
        caption=f"Фото «{plant.name}» обновлено ✅",
    )
    file_id = message.photo[-1].file_id
    await plants_repo.set_photo(session, plant_id, file_id)
    return {"ok": True, "photo_file_id": file_id}


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
