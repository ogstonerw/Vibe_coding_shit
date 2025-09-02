#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import signal
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class SystemRunner:
    def __init__(self):
        self.bot = None
        self.running = True
        
    async def shutdown(self, signal=None):
        """Корректное завершение работы системы"""
        print(f"\n⏹️ Получен сигнал остановки {signal}")
        self.running = False
        
        if self.bot and self.bot.client:
            try:
                print("🔌 Отключение Telegram клиента...")
                await self.bot.client.disconnect()
                print("✅ Telegram клиент отключен")
            except Exception as e:
                print(f"⚠️ Ошибка при отключении: {e}")
        
        print("🎵 Шарманка остановлена!")
        sys.exit(0)
    
    async def run_system(self):
        """Запуск интегрированной системы"""
        print("🎵 ЗАПУСКАЕМ ШАРМАНКУ!")
        print("=" * 50)
        
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
        
        self.bot = ImprovedTradingBot()
        
        try:
            # Инициализируем основной бот
            await self.bot.initialize()
            self.bot.setup_message_handlers()
            
            print("\n✅ Основной бот инициализирован")
            print("🎯 Бот слушает каналы:")
            for k, v in self.bot.channel_entities.items():
                print(f"   - {k}: {getattr(v, 'title', v.id)}")
            
            print(f"\n💡 Режим: {'DRY_RUN (симуляция)' if dry_run else 'РЕАЛЬНАЯ ТОРГОВЛЯ'}")
            
            # Проверяем бота управления
            if bot_token and allowed_users:
                print("✅ Бот управления запущен параллельно")
                print("   Команды: /start, /help, /history, /equity, /stats, /dryrun_on, /dryrun_off")
                print("   Найдите бота в Telegram и отправьте /start")
            else:
                print("⚠️ Бот управления не запущен (отсутствует токен или пользователи)")
            
            print("\n🎵 ШАРМАНКА ЗАПУЩЕНА!")
            print("   Для остановки: Ctrl+C")
            print("   Система работает в фоновом режиме...")
            
            # Запускаем основную систему
            await self.bot.run()
            
        except KeyboardInterrupt:
            await self.shutdown("KeyboardInterrupt")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            await self.shutdown("Exception")

async def main():
    """Основная функция"""
    runner = SystemRunner()
    
    # Настраиваем обработчики сигналов
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(runner.shutdown("SIGINT")))
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(runner.shutdown("SIGTERM")))
    
    await runner.run_system()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Остановка системы...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
