# ingest/tg_reader.py
import asyncio
import logging
from typing import Optional, Callable, Awaitable
from telethon import TelegramClient, events
from telethon.tl.types import Channel
from config.settings import settings

log = logging.getLogger(__name__)

# Тип коллбэка, который ты реализуешь в своем коде:
# async def parse_and_route(source: str, text: str): ...
OnMessage = Callable[[str, str], Awaitable[None]]

async def _resolve_channel_by_link_or_name(client: TelegramClient, link: Optional[str], name_substr: Optional[str]) -> Channel:
    """
    Пытается найти канал: сначала по инвайт-ссылке (https://t.me/+XXXX),
    если не получилось — по подстроке в названии среди твоих диалогов.
    """
    # 1) по ссылке
    if link:
        try:
            ent = await client.get_entity(link)
            if isinstance(ent, Channel):
                return ent
        except Exception as e:
            log.warning("Cannot resolve by link %s: %s", link, e)

    # 2) по названию
    if name_substr:
        async for dialog in client.iter_dialogs():
            if isinstance(dialog.entity, Channel):
                if name_substr.lower() in (dialog.name or "").lower():
                    return dialog.entity

    raise RuntimeError(f"Channel not found. link={link} name_part={name_substr}")

async def start_telethon_reader(settings, on_message: OnMessage = None):
    """
    Запускает Telethon-клиент, подписывается на 2 канала (скальпинг/интрадей),
    и на каждое новое сообщение вызывает on_message(source, text).
    Если on_message не передан — логируем текст.
    """
    session_name = settings.TG_SESSION
    client = TelegramClient(session_name, settings.TG_API_ID, settings.TG_API_HASH)

    scalping_link = getattr(settings, "TG_SOURCE_SCALPING_LINK", None)
    intraday_link = getattr(settings, "TG_SOURCE_INTRADAY_LINK", None)
    scalping_name = getattr(settings, "TG_SOURCE_SCALPING_NAME", None)
    intraday_name = getattr(settings, "TG_SOURCE_INTRADAY_NAME", None)

    await client.start()  # если .session существует — НЕ спросит код, иначе попросит один раз и сохранит

    scalping = await _resolve_channel_by_link_or_name(client, scalping_link, scalping_name)
    intraday = await _resolve_channel_by_link_or_name(client, intraday_link, intraday_name)

    log.info("Resolved channels: SCALPING id=%s title=%s | INTRADAY id=%s title=%s",
             scalping.id, scalping.title, intraday.id, intraday.title)

    @client.on(events.NewMessage(chats=scalping))
    async def handler_scalping(event):
        text = event.raw_text or ""
        log.info("[SCALPING] %s", text[:200].replace("\n", " "))
        if on_message:
            await on_message("SCALPING", text)

    @client.on(events.NewMessage(chats=intraday))
    async def handler_intraday(event):
        text = event.raw_text or ""
        log.info("[INTRADAY] %s", text[:200].replace("\n", " "))
        if on_message:
            await on_message("INTRADAY", text)

    log.info("Telegram reader started. Listening SCALPING & INTRADAY.")

    async with client:
        await client.run_until_disconnected()
