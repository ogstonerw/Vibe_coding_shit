#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_integration():
    """Простой тест интеграции"""
    print("🎯 ТЕСТ ИНТЕГРАЦИИ")
    print("=" * 40)
    
    # Проверяем основные переменные
    print("📋 Проверка конфигурации:")
    
    api_id = os.getenv('API_ID', '')
    api_hash = os.getenv('API_HASH', '')
    bot_token = os.getenv('TGBOT_TOKEN', '')
    owner_id = os.getenv('TG_OWNER_ID', '0')
    owner_id_2 = os.getenv('TG_OWNER_ID_2', '0')
    
    print(f"   API_ID: {'✅ Установлен' if api_id else '❌ Не установлен'}")
    print(f"   API_HASH: {'✅ Установлен' if api_hash else '❌ Не установлен'}")
    print(f"   TGBOT_TOKEN: {'✅ Установлен' if bot_token else '❌ Не установлен'}")
    print(f"   TG_OWNER_ID: {owner_id}")
    print(f"   TG_OWNER_ID_2: {owner_id_2}")
    
    # Проверяем разрешенных пользователей
    allowed_users = []
    try:
        if owner_id != "0":
            allowed_users.append(int(owner_id))
        if owner_id_2 != "0":
            allowed_users.append(int(owner_id_2))
    except ValueError:
        pass
    
    print(f"   Разрешенные пользователи: {allowed_users}")
    
    # Проверяем режим
    dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
    print(f"   DRY_RUN: {'✅ Включен' if dry_run else '❌ Выключен'}")
    
    if not api_id or not api_hash:
        print("\n❌ API_ID или API_HASH не установлены")
        return
    
    print("\n🚀 Запуск интегрированной системы...")
    
    # Импортируем основной бот
    from main import ImprovedTradingBot
    
    bot = ImprovedTradingBot()
    
    try:
        # Инициализируем основной бот
        await bot.initialize()
        bot.setup_message_handlers()
        
        print("\n✅ Основной бот инициализирован")
        print("🎯 Бот слушает каналы:")
        for k, v in bot.channel_entities.items():
            print(f"   - {k}: {getattr(v, 'title', v.id)}")
        
        print(f"\n💡 Режим: {'DRY_RUN (симуляция)' if dry_run else 'РЕАЛЬНАЯ ТОРГОВЛЯ'}")
        
        # Проверяем бота управления
        if bot_token and allowed_users:
            print("✅ Бот управления будет запущен параллельно")
            print("   Команды: /start, /help, /history, /equity, /stats, /dryrun_on, /dryrun_off")
        else:
            print("⚠️ Бот управления не будет запущен (отсутствует токен или пользователи)")
        
        print("\n🎵 ШАРМАНКА ЗАПУЩЕНА!")
        print("   Для остановки: Ctrl+C")
        
        # Запускаем основную систему
        await bot.run()
        
    except KeyboardInterrupt:
        print("\n⏹️ Остановка системы...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if bot.client:
            await bot.client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_integration())
