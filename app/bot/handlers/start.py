from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_menu_kb, onboarding_kb
from app.services import onboarding

router = Router()


class Onboarding(StatesGroup):
    waiting_family_name = State()
    waiting_invite_code = State()


async def _show_main_menu(message: Message, session: AsyncSession, user_id: int):
    family = await onboarding.get_user_family(session, user_id)
    bot_user = await message.bot.me()
    link = onboarding.invite_link(bot_user.username, family)
    await message.answer(
        f"🏡 Семья: <b>{family.name}</b>\n"
        f"Код приглашения: <code>{family.invite_code}</code>\n"
        f"Ссылка: {link}\n\n"
        "Открывай сад, добавляй растения и отмечай полив 👇",
        reply_markup=main_menu_kb(),
        disable_web_page_preview=True,
    )


@router.message(CommandStart(deep_link=True))
async def start_with_code(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
):
    await state.clear()
    # Уже в семье — просто показываем меню
    if await onboarding.get_user_family(session, message.from_user.id):
        await _show_main_menu(message, session, message.from_user.id)
        return

    family = await onboarding.join_family(session, message.from_user.id, command.args)
    if family is None:
        await message.answer(
            "Не нашёл семью по этому коду 😕 Проверь ссылку или создай свою семью:",
            reply_markup=onboarding_kb(),
        )
        return
    await message.answer(f"Добро пожаловать в семью <b>{family.name}</b>! 🎉")
    await _show_main_menu(message, session, message.from_user.id)


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    if await onboarding.get_user_family(session, message.from_user.id):
        await _show_main_menu(message, session, message.from_user.id)
        return
    await message.answer(
        "Привет! Я помогаю семье вместе ухаживать за растениями 🪴\n\n"
        "Создай семью или присоединись к существующей:",
        reply_markup=onboarding_kb(),
    )


@router.callback_query(F.data == "onb:create")
async def onb_create(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Onboarding.waiting_family_name)
    await callback.message.answer(
        "Как назовём семью? Например: <i>Ивановы</i> или <i>Наш дом</i>"
    )
    await callback.answer()


@router.message(Onboarding.waiting_family_name, F.text)
async def onb_family_name(
    message: Message, session: AsyncSession, state: FSMContext
):
    await state.clear()
    family = await onboarding.create_family(
        session, message.from_user.id, message.text
    )
    await message.answer(f"Семья <b>{family.name}</b> создана! ✅")
    await _show_main_menu(message, session, message.from_user.id)


@router.callback_query(F.data == "onb:join")
async def onb_join(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Onboarding.waiting_invite_code)
    await callback.message.answer("Введи код приглашения (8 символов):")
    await callback.answer()


@router.message(Onboarding.waiting_invite_code, F.text)
async def onb_invite_code(
    message: Message, session: AsyncSession, state: FSMContext
):
    family = await onboarding.join_family(
        session, message.from_user.id, message.text
    )
    if family is None:
        await message.answer("Такого кода нет 😕 Попробуй ещё раз:")
        return
    await state.clear()
    await message.answer(f"Добро пожаловать в семью <b>{family.name}</b>! 🎉")
    await _show_main_menu(message, session, message.from_user.id)


@router.callback_query(F.data == "invite")
async def show_invite(callback: CallbackQuery, session: AsyncSession):
    family = await onboarding.get_user_family(session, callback.from_user.id)
    if family is None:
        await callback.answer("Сначала создай семью — /start", show_alert=True)
        return
    bot_user = await callback.bot.me()
    link = onboarding.invite_link(bot_user.username, family)
    await callback.message.answer(
        f"Перешли эту ссылку члену семьи:\n{link}\n\n"
        f"Или пусть введут код: <code>{family.invite_code}</code>",
        disable_web_page_preview=True,
    )
    await callback.answer()
