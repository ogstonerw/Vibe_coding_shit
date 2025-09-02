#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from bot.tg_control import start_control_bot

async def test_control_bot():
    """Тест бота управления"""
    print("🧪 Тестирование бота управления...")
    
    # Проверяем переменные окружения
    token = os.getenv("TGBOT_TOKEN", "")
    owner_id = os.getenv("TG_OWNER_ID", "0")
    owner_id_2 = os.getenv("TG_OWNER_ID_2", "0")
    
    print(f"📋 Конфигурация:")
    print(f"   TGBOT_TOKEN: {'✅ Установлен' if token else '❌ Не установлен'}")
    if token:
        print(f"   Токен: {token[:10]}...{token[-10:]}")
    print(f"   TG_OWNER_ID: {owner_id}")
    print(f"   TG_OWNER_ID_2: {owner_id_2}")
    
    # Проверяем, загружается ли .env
    from dotenv import load_dotenv
    load_dotenv()
    
    # Повторно проверяем после load_dotenv
    token_after = os.getenv("TGBOT_TOKEN", "")
    owner_id_after = os.getenv("TG_OWNER_ID", "0")
    owner_id_2_after = os.getenv("TG_OWNER_ID_2", "0")
    
    print(f"\n📋 После load_dotenv():")
    print(f"   TGBOT_TOKEN: {'✅ Установлен' if token_after else '❌ Не установлен'}")
    print(f"   TG_OWNER_ID: {owner_id_after}")
    print(f"   TG_OWNER_ID_2: {owner_id_2_after}")
    
    # Проверяем, есть ли хотя бы один разрешенный пользователь
    allowed_users = []
    try:
        if owner_id_after != "0" and owner_id_after != "@728834902":  # Исключаем неправильный формат
            allowed_users.append(int(owner_id_after))
        elif owner_id_after == "728834902":  # Правильный числовой формат
            allowed_users.append(728834902)
        if owner_id_2_after != "0":
            allowed_users.append(int(owner_id_2_after))
    except ValueError:
        pass
    
    print(f"   Разрешенные пользователи: {allowed_users}")
    
    if not token_after or not allowed_users:
        print("⚠️ Бот управления не будет запущен - отсутствуют ключевые переменные")
        print("   Добавьте в .env:")
        print("   TGBOT_TOKEN=ваш_токен_от_botfather")
        print("   TG_OWNER_ID=ваш_user_id")
        print("   TG_OWNER_ID_2=второй_user_id (опционально)")
        return
    
    print("\n🚀 Запуск бота управления...")
    print("   Команды для тестирования:")
    print("   /start - приветствие")
    print("   /help - справка")
    print("   /history - история сделок")
    print("   /equity - информация о депозите")
    print("   /stats - статистика")
    print("   /dryrun_on /dryrun_off - переключение режима")
    
    try:
        await start_control_bot()
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота управления...")
    except Exception as e:
        print(f"❌ Ошибка бота управления: {e}")

if __name__ == "__main__":
    asyncio.run(test_control_bot())
