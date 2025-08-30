#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, time, hmac, hashlib, base64, json, asyncio
from typing import Optional
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import Channel
import httpx

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
TG_SESSION = os.getenv("TG_SESSION", "signal_trader")
TG_PHONE = os.getenv("TG_PHONE") or os.getenv("PHONE")
SCALPING_LINK = os.getenv("TG_SOURCE_SCALPING_LINK", "")
SCALPING_NAME = os.getenv("TG_SOURCE_SCALPING_NAME", "")
INTRADAY_LINK = os.getenv("TG_SOURCE_INTRADAY_LINK", "")
INTRADAY_NAME = os.getenv("TG_SOURCE_INTRADAY_NAME", "")

EXCHANGE = (os.getenv("EXCHANGE","bitget")).lower()

# Bitget
BITGET_BASE = os.getenv("BITGET_BASE","https://api.bitget.com").rstrip("/")
BITGET_API_KEY = os.getenv("BITGET_API_KEY","")
BITGET_API_SECRET = os.getenv("BITGET_API_SECRET","")
BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE","")

# Bybit
BYBIT_BASE = os.getenv("BYBIT_BASE","https://api.bybit.com").rstrip("/")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY","")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET","")

async def resolve_by_link_or_name(client: TelegramClient, link: str, name: str) -> Optional[Channel]:
    if link:
        try:
            ent = await client.get_entity(link)
            if isinstance(ent, Channel):
                return ent
        except Exception as e:
            print(f"⚠️  Не удалось получить канал по ссылке {link}: {e}")
    if name:
        async for dialog in client.iter_dialogs():
            if isinstance(dialog.entity, Channel):
                if name.lower() in (dialog.name or "").lower():
                    return dialog.entity
    return None

async def check_telegram():
    print("▶️  TELEGRAM CHECK")
    client = TelegramClient(TG_SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        if not TG_PHONE:
            print("❌ Нет авторизации и TG_PHONE не задан. Укажи TG_PHONE в .env")
            return False
        await client.start(phone=TG_PHONE)
    me = await client.get_me()
    print(f"✅ Авторизован как: {me.first_name} (id={me.id})")

    scalping = await resolve_by_link_or_name(client, SCALPING_LINK, SCALPING_NAME)
    intraday = await resolve_by_link_or_name(client, INTRADAY_LINK, INTRADAY_NAME)
    if not scalping or not intraday:
        print("❌ Каналы не найдены. Проверь TG_SOURCE_*_LINK или *_NAME в .env")
        await client.disconnect()
        return False

    print(f"✅ SCALPING: id={scalping.id}, title={getattr(scalping,'title',None)}")
    print(f"✅ INTRADAY: id={intraday.id}, title={getattr(intraday,'title',None)}")

    # пробуем прочитать последние 1–2 сообщения для проверки доступа
    try:
        msgs = await client.get_messages(scalping, limit=2)
        print(f"📝 Последние сообщения SCALPING: {len(msgs)} шт.")
        msgs = await client.get_messages(intraday, limit=2)
        print(f"📝 Последние сообщения INTRADAY: {len(msgs)} шт.")
    except Exception as e:
        print(f"⚠️  Не удалось прочитать сообщения: {e}")

    await client.disconnect()
    return True

# ---------- Bitget ----------
def bitget_headers(ts: str, method: str, path: str, body: str, secret: str, key: str, passphrase: str):
    msg = f"{ts}{method}{path}{body}".encode()
    sig = base64.b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).decode()
    return {
        "ACCESS-KEY": key,
        "ACCESS-SIGN": sig,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json"
    }

def check_bitget():
    print("▶️  BITGET CHECK")
    try:
        with httpx.Client(timeout=10.0) as http:
            # Публичный пинг (серверное время)
            r = http.get(BITGET_BASE + "/api/spot/v1/public/time")
            print(f"⏱️  Public ping status: {r.status_code}")
            # Приватный минимальный вызов (пример: серверное время через приват? или аккаунт)
            # [Неподтверждено] Эндпоинт аккаунта может отличаться в зависимости от продукта
            path = "/api/mix/v1/account/accounts?productType=umcbl"
            ts = str(int(time.time() * 1000))
            headers = bitget_headers(ts, "GET", path, "", BITGET_API_SECRET, BITGET_API_KEY, BITGET_PASSPHRASE)
            r2 = http.get(BITGET_BASE + path, headers=headers)
            print(f"🔐 Private status: {r2.status_code}")
            if r2.status_code == 200:
                print("✅ Bitget приватный доступ работает")
                # print("Body:", r2.text)
                return True
            else:
                print(f"⚠️  Bitget приватный ответ: {r2.status_code} {r2.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ Bitget ошибка: {e}")
        return False

# ---------- Bybit ----------
def bybit_sign(params: dict, secret: str) -> str:
    # [Неподтверждено] V5: подпись = HMAC_SHA256(secret, concat(sorted(params))) в зависимости от эндпоинта.
    # Здесь даем минимальную проверку через публичный пинг и простой приватный GET с timestamp.
    payload = "&".join([f"{k}={params[k]}" for k in sorted(params)])
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

def check_bybit():
    print("▶️  BYBIT CHECK")
    try:
        with httpx.Client(timeout=10.0) as http:
            # Публичный пинг
            r = http.get(BYBIT_BASE + "/v5/market/time")
            print(f"⏱️  Public ping status: {r.status_code}")
            # Приватный (минимальный пример: серверное время/баланс — зависит от твоего аккаунта)
            # [Неподтверждено] Пример параметров:
            ts = str(int(time.time() * 1000))
            params = {"api_key": BYBIT_API_KEY, "timestamp": ts}
            sign = bybit_sign(params, BYBIT_API_SECRET)
            params["sign"] = sign
            r2 = http.get(BYBIT_BASE + "/v5/account/wallet-balance", params=params)
            print(f"🔐 Private status: {r2.status_code}")
            if r2.status_code == 200:
                print("✅ Bybit приватный доступ работает")
                # print("Body:", r2.text)
                return True
            else:
                print(f"⚠️  Bybit приватный ответ: {r2.status_code} {r2.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ Bybit ошибка: {e}")
        return False

async def main():
    ok_tg = await check_telegram()
    if EXCHANGE == "bitget":
        ok_ex = check_bitget()
    else:
        ok_ex = check_bybit()
    print("\n==== SUMMARY ====")
    print(f"Telegram: {'OK' if ok_tg else 'FAIL'}")
    print(f"{EXCHANGE.upper()}: {'OK' if ok_ex else 'FAIL'}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
