#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from aiogram import Bot
from dotenv import load_dotenv

load_dotenv()

async def get_my_id():
    """Получаем ваш user_id через бота"""
    
    token = os.getenv("TGBOT_TOKEN", "")
    if not token:
        print("❌ TGBOT_TOKEN не установлен в .env")
        return
    
    print("🤖 Создаем бота для получения вашего ID...")
    bot = Bot(token)
    
    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"✅ Бот подключен: @{bot_info.username}")
        
        print("\n📋 Инструкция:")
        print("1. Найдите бота @{} в Telegram".format(bot_info.username))
        print("2. Отправьте ему любое сообщение (например, /start)")
        print("3. Скопируйте ваш user_id из сообщения ниже")
        print("\n⏳ Ожидаем сообщение...")
        
        # Создаем простой обработчик
        @bot.message_handler()
        async def handle_message(message):
            user_id = message.from_user.id
            username = message.from_user.username
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            
            print(f"\n🎯 Получен user_id!")
            print(f"   ID: {user_id}")
            print(f"   Username: @{username}" if username else "   Username: не установлен")
            print(f"   Имя: {first_name} {last_name or ''}")
            print(f"\n📝 Обновите в .env:")
            print(f"TG_OWNER_ID={user_id}")
            
            await message.reply(f"Ваш user_id: {user_id}")
            await bot.stop_polling()
        
        # Запускаем бота
        await bot.polling(timeout=60)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(get_my_id())
