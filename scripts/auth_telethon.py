#!/usr/bin/env python3
"""One-time Telethon authorization script.

Run this locally on your machine to create a .session file interactively.
It will prompt for phone/code/2FA if required and save the session file specified
by TG_SESSION in your .env (or default 'signal_trader').

Usage:
    python scripts/auth_telethon.py

This script is NOT used in production. Keep the created .session file secure.
"""
import sys, os
# ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv('API_ID') or 0)
API_HASH = os.getenv('API_HASH') or ''
TG_SESSION = os.path.abspath(os.getenv('TG_SESSION', 'signal_trader'))
TG_PHONE = os.getenv('TG_PHONE', '')

if not API_ID or not API_HASH:
    print('API_ID/API_HASH not set in .env')
    raise SystemExit(1)

print('Session path:', TG_SESSION)
client = TelegramClient(TG_SESSION, API_ID, API_HASH)

async def main():
    print('Starting interactive authorization...')
    try:
        # If TG_PHONE is set in .env, pass it to start() so Telethon won't ask for phone
        if TG_PHONE:
            print('Using TG_PHONE from .env to prefill phone prompt')
            await client.start(phone=TG_PHONE)
        else:
            await client.start()
    except EOFError:
        # Happens when running in a non-interactive environment
        print('\nInput not available: run this script in an interactive terminal (powerShell)')
        print('or set TG_PHONE in your .env to prefill the phone and re-run.')
        raise
    me = await client.get_me()
    print('Authorized as', getattr(me, 'username', None) or getattr(me, 'first_name', None), f"(id={me.id})")
    await client.disconnect()

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nCancelled')
