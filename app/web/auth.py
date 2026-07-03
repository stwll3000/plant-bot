"""Проверка Telegram WebApp initData.

Mini App шлёт initData в заголовке Authorization: tma <initData>.
Подпись проверяется по схеме из документации Telegram:
secret_key = HMAC_SHA256(key="WebAppData", data=bot_token)
hash       = HMAC_SHA256(key=secret_key, data=data_check_string)
"""
import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from app.config import settings


def validate_init_data(init_data: str) -> dict | None:
    """Возвращает данные пользователя Telegram или None, если подпись неверна."""
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        secret_key = hmac.new(
            b"WebAppData", settings.bot_token.encode(), hashlib.sha256
        ).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None
        return json.loads(parsed["user"])
    except (KeyError, ValueError):
        return None
