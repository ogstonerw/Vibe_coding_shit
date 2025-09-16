"""
User-клиент Telethon для чтения каналов.
Безопасен: только connect(), без start/sign_in/log_out.
Сессия: StringSession из .env или FileSession (data/sessions/user.session).
"""
import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession, FileSession
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_STRING_SESSION = os.getenv("TELEGRAM_STRING_SESSION")
TELEGRAM_SESSION_FILE = os.getenv("TELEGRAM_SESSION_FILE", "data/sessions/user.session")

import pathlib
pathlib.Path("data/sessions").mkdir(parents=True, exist_ok=True)

_user_client = None
_user_lock = asyncio.Lock()

async def get_user_client():
    """
    Возвращает синглтон Telethon-клиента для чтения каналов.
    Не вызывает start/sign_in/log_out. Только connect().
    """
    global _user_client
    async with _user_lock:
        if _user_client is None:
            if TELEGRAM_STRING_SESSION:
                session = StringSession(TELEGRAM_STRING_SESSION)
            else:
                session = FileSession(TELEGRAM_SESSION_FILE)
            _user_client = TelegramClient(
                session,
                TELEGRAM_API_ID,
                TELEGRAM_API_HASH,
                device_model="ServerWorker",
                system_version="Linux",
                app_version="1.0.0",
                lang_code="ru"
            )
            await _user_client.connect()
            if not await _user_client.is_user_authorized():
                raise RuntimeError("User session not authorized. Проверьте TELEGRAM_STRING_SESSION или user.session.")
        return _user_client
