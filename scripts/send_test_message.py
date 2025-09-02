#!/usr/bin/env python3
"""Send a test message via Telethon session to configured channel.

Usage:
  python scripts/send_test_message.py "Hello world"

It will use TG_SESSION and TG_SOURCE_SCALPING_LINK / NAME from .env.
"""
import sys, os
# ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()
from telethon import TelegramClient

API_ID = int(os.getenv('API_ID') or 0)
API_HASH = os.getenv('API_HASH') or ''
TG_SESSION = os.path.abspath(os.getenv('TG_SESSION','signal_trader'))
SCALPING_LINK = os.getenv('TG_SOURCE_SCALPING_LINK') or None
SCALPING_NAME = os.getenv('TG_SOURCE_SCALPING_NAME') or None

if len(__import__('sys').argv) < 2:
    print('Provide message text')
    raise SystemExit(2)

text = __import__('sys').argv[1]

client = TelegramClient(TG_SESSION, API_ID, API_HASH)

async def main():
    await client.connect()
    if not await client.is_user_authorized():
        print('Session not authorized. Run scripts/auth_telethon.py locally to create session file.')
        await client.disconnect()
        return
    # resolve target
    target = None
    if SCALPING_LINK:
        try:
            target = await client.get_entity(SCALPING_LINK)
        except Exception:
            target = None
    if not target and SCALPING_NAME:
        async for d in client.iter_dialogs():
            if SCALPING_NAME.lower() in (d.name or '').lower():
                target = d.entity
                break
    if not target:
        print('Target channel not found')
        await client.disconnect()
        return
    await client.send_message(target, text)
    print('Sent')
    await client.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
