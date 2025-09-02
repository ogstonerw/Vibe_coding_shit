#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем токен из .env
TOKEN = os.getenv("TGBOT_TOKEN", "")

async def start_command(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    response = f"🎯 Ваш user_id: <b>{user_id}</b>\n"
    if username:
        response += f"Username: @{username}\n"
    response += f"Имя: {first_name} {last_name or ''}"
    
    await message.answer(response, parse_mode="HTML")
    
    # Выводим в консоль для копирования
    print(f"\n🎯 Получен user_id!")
    print(f"   ID: {user_id}")
    print(f"   Username: @{username}" if username else "   Username: не установлен")
    print(f"   Имя: {first_name} {last_name or ''}")
    print(f"\n📝 Обновите в .env:")
    print(f"TG_OWNER_ID={user_id}")

async def main():
    """Основная функция"""
    if not TOKEN:
        print("❌ TGBOT_TOKEN не установлен в .env")
        print("   Добавьте в .env: TGBOT_TOKEN=ваш_токен")
        return
    
    print("🤖 Создаем бота для получения вашего ID...")
    
    try:
        # Создаем бота и диспетчер
        bot = Bot(token=TOKEN)
        dp = Dispatcher()
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"✅ Бот подключен: @{bot_info.username}")
        
        # Регистрируем обработчик
        dp.message.register(start_command, Command("start"))
        
        print("\n📋 Инструкция:")
        print("1. Найдите бота @{} в Telegram".format(bot_info.username))
        print("2. Отправьте ему команду /start")
        print("3. Скопируйте ваш user_id из сообщения выше")
        print("\n⏳ Ожидаем команду /start...")
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if 'bot' in locals():
            await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
