from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

from app.config import settings


def onboarding_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏡 Создать семью", callback_data="onb:create")],
            [
                InlineKeyboardButton(
                    text="🔑 Присоединиться по коду", callback_data="onb:join"
                )
            ],
        ]
    )


def main_menu_kb() -> InlineKeyboardMarkup:
    rows = []
    if settings.webapp_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🪴 Открыть сад",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="📖 Последние поливы", callback_data="log")]
    )
    rows.append(
        [InlineKeyboardButton(text="🔗 Пригласить в семью", callback_data="invite")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def water_kb(plant_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💧 Полил(а)", callback_data=f"water:{plant_id}"
                )
            ]
        ]
    )


def plants_choice_kb(plants, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=p.name, callback_data=f"{prefix}:{p.id}")]
        for p in plants
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
