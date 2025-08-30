from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("TG_SESSION", "signal_trader")

client = TelegramClient(SESSION, API_ID, API_HASH)

async def main():
    await client.connect()
    if not await client.is_user_authorized():
        print(f"❌ Session '{SESSION}' NOT authorized.")
    else:
        me = await client.get_me()
        print(f"✅ Session '{SESSION}' is authorized as {me.first_name} (@{me.username}) id={me.id}")

with client:
    client.loop.run_until_complete(main())
