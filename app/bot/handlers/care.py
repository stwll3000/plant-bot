from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import plants_choice_kb
from app.db.repositories import care as care_repo
from app.db.repositories import plants as plants_repo
from app.services import care as care_service
from app.services import onboarding
from app.services.reminders import CARE_EMOJI

router = Router()


class PhotoFlow(StatesGroup):
    waiting_plant_choice = State()


CARE_DONE_WORD = {"watering": "Полил(а)", "spraying": "Опрыскал(а)"}


@router.callback_query(F.data.startswith("care:"))
async def care_from_chat(callback: CallbackQuery, session: AsyncSession):
    _, care_code, plant_id = callback.data.split(":")
    await _mark_from_chat(callback, session, int(plant_id), care_code)


@router.callback_query(F.data.startswith("water:"))
async def water_from_chat(callback: CallbackQuery, session: AsyncSession):
    # Кнопки в старых напоминаниях, отправленных до появления care:
    plant_id = int(callback.data.split(":")[1])
    await _mark_from_chat(callback, session, plant_id, "watering")


async def _mark_from_chat(
    callback: CallbackQuery, session: AsyncSession, plant_id: int, care_code: str
):
    location = await care_service.mark_done(
        session, plant_id, callback.from_user.id, care_code
    )
    if location is None:
        await callback.answer("Растение не найдено 😕", show_alert=True)
        return

    done_word = CARE_DONE_WORD.get(care_code, "Сделано")
    await callback.answer("Записал! ✅")
    await callback.message.edit_text(
        callback.message.html_text
        + f"\n\n✅ {done_word}: {callback.from_user.first_name}",
        reply_markup=None,
    )


@router.message(Command("log"))
async def show_log_cmd(message: Message, session: AsyncSession):
    await _send_log(message, session, message.from_user.id)


@router.callback_query(F.data == "log")
async def show_log_cb(callback: CallbackQuery, session: AsyncSession):
    await _send_log(callback.message, session, callback.from_user.id)
    await callback.answer()


async def _send_log(message: Message, session: AsyncSession, user_id: int):
    family = await onboarding.get_user_family(session, user_id)
    if family is None:
        await message.answer("Сначала создай семью — /start")
        return

    rows = await care_repo.recent_logs(session, family.id, limit=10)
    if not rows:
        await message.answer("Журнал пока пуст — никто ничего не поливал 🌵")
        return

    lines = ["📖 <b>Последние записи:</b>\n"]
    for log, user, plant, room, prop, care_type in rows:
        when = log.done_at.strftime("%d.%m %H:%M")
        emoji = CARE_EMOJI.get(care_type.code, "🪴")
        lines.append(
            f"{emoji} {user.first_name} — <b>{plant.name}</b> "
            f"({prop.name}, {room.name}) · {when}"
        )
    await message.answer("\n".join(lines))


@router.message(F.photo)
async def photo_received(
    message: Message, session: AsyncSession, state: FSMContext
):
    """Фото растения: пользователь шлёт фото, потом выбирает растение."""
    family = await onboarding.get_user_family(session, message.from_user.id)
    if family is None:
        await message.answer("Сначала создай семью — /start")
        return

    plants = await plants_repo.get_family_plants(session, family.id)
    if not plants:
        await message.answer("Пока нет ни одного растения — добавь его в Mini App 🪴")
        return

    # Берём самое большое разрешение фото
    file_id = message.photo[-1].file_id
    await state.set_state(PhotoFlow.waiting_plant_choice)
    await state.update_data(photo_file_id=file_id)
    await message.answer(
        "Отличное фото! К какому растению его привязать?",
        reply_markup=plants_choice_kb(plants, prefix="setphoto"),
    )


@router.callback_query(PhotoFlow.waiting_plant_choice, F.data.startswith("setphoto:"))
async def photo_assign(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
):
    plant_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    await plants_repo.set_photo(session, plant_id, data["photo_file_id"])
    await callback.message.edit_text("Фото сохранено! ✅")
    await callback.answer()
