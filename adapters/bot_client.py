"""
Bot-клиент Telethon для отправки уведомлений.
Безопасен: отдельная сессия, не читает каналы.
Инициализация через start(bot_token=...).
Сессия: data/sessions/bot.session
"""
import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import FileSession
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TGBOT_TOKEN = os.getenv("TGBOT_TOKEN", "")

import pathlib
pathlib.Path("data/sessions").mkdir(parents=True, exist_ok=True)

_bot_client = None
_bot_lock = asyncio.Lock()

async def get_bot_client():
    """
    Возвращает синглтон Telethon-клиента для отправки уведомлений (бот).
    Использует start(bot_token=...).
    """
    global _bot_client
    async with _bot_lock:
        if _bot_client is None:
            session = FileSession("data/sessions/bot.session")
            _bot_client = TelegramClient(
                session,
                TELEGRAM_API_ID,
                TELEGRAM_API_HASH,
                device_model="ServerWorker",
                system_version="Linux",
                app_version="1.0.0",
                lang_code="ru"
            )
            await _bot_client.start(bot_token=TGBOT_TOKEN)
        return _bot_client
