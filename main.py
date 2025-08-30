#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import sys

from datetime import datetime
from typing import Optional, Dict

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import Channel

from improved_signal_parser import ImprovedSignalParser, TradingSignal
from bitget_integration import BitgetTrader, load_bitget_config
from trader.executor import Executor
from market.watcher import Watcher
from bot.tg_control import start_control_bot

# 1) Загружаем .env (НЕ data.env)
load_dotenv()

# 2) Конфиг из окружения
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
TG_SESSION = os.getenv('TG_SESSION', 'signal_trader')
PHONE = os.getenv('PHONE') or os.getenv('TG_PHONE')

# Приватные каналы: либо ссылка, либо часть названия
SCALPING_LINK = os.getenv('TG_SOURCE_SCALPING_LINK') or ""
SCALPING_NAME = os.getenv('TG_SOURCE_SCALPING_NAME') or ""
INTRADAY_LINK = os.getenv('TG_SOURCE_INTRADAY_LINK') or ""
INTRADAY_NAME = os.getenv('TG_SOURCE_INTRADAY_NAME') or ""

# Риск и логика
DRY_RUN = (os.getenv('DRY_RUN', 'true').lower() == 'true')
EQUITY_USDT = float(os.getenv('EQUITY_USDT', '0'))
SPLIT_SCALPING_PCT = float(os.getenv('SPLIT_SCALPING_PCT', '15'))
SPLIT_INTRADAY_PCT = float(os.getenv('SPLIT_INTRADAY_PCT', '85'))
RISK_TOTAL_CAP_PCT = float(os.getenv('RISK_TOTAL_CAP_PCT', '3.0'))
RISK_LEG_PCT = float(os.getenv('RISK_LEG_PCT', '1.5'))
LEVERAGE_MIN = int(os.getenv('LEVERAGE_MIN', '10'))
LEVERAGE_MAX = int(os.getenv('LEVERAGE_MAX', '25'))
BREAKEVEN_AFTER_TP = int(os.getenv('BREAKEVEN_AFTER_TP', '2'))
TIME_STOP_MIN = int(os.getenv('TIME_STOP_MIN', '240'))

# Настройка кодировки консоли (безопасно)
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
except Exception:
    pass


class ImprovedTradingBot:
    """Улучшенный торговый бот с обученным парсером"""

    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.parser = ImprovedSignalParser()
        self.bitget_trader: Optional[BitgetTrader] = None
        self.signal_manager = SignalManager()
        self.channel_entities: Dict[str, Channel] = {}
        self.channel_source_by_id: Dict[int, str] = {}  # channel.id -> SCALPING|INTRADAY
        self.phone = PHONE
        self.watcher: Optional[Watcher] = None
        self._synthetic_price = None  # для DRY_RUN синтетический «тик»

        self.stats = {
            'signals_processed': 0,
            'signals_executed': 0,
            'total_profit': 0.0,
            'start_time': datetime.now()
        }

    async def initialize(self):
        print("🚀 Инициализация улучшенного торгового бота...")

        # 3) Создаем клиент с именем сессии из .env (устойчивый логин)
        self.client = TelegramClient(TG_SESSION, API_ID, API_HASH)
        await self.client.connect()

        if not await self.client.is_user_authorized():
            if not self.phone:
                try:
                    self.phone = input("Введите номер телефона Telegram в формате +79991234567: ").strip()
                except Exception:
                    self.phone = None
            # start сохранит .session → далее без повторных кодов
            await self.client.start(phone=self.phone)

        print("✅ Telegram клиент подключен")

        # Bitget трейдер
        if not DRY_RUN:
            try:
                config = load_bitget_config()
                if config:
                    self.bitget_trader = BitgetTrader(config)
                    print("✅ Bitget трейдер подключен")
                else:
                    print("⚠️ Bitget конфигурация не найдена")
            except Exception as e:
                print(f"❌ Ошибка подключения к Bitget: {e}")
        else:
            print("🔧 Режим DRY_RUN - реальная торговля отключена")

        # создаём watcher (перевод SL в БУ после TP2)
        def on_breakeven(plan: dict):
            side = plan["side"]
            entry = plan["entry"]
            be = entry + 1.0 if side == "SHORT" else entry - 1.0  # небольшой буфер в 1$
            print(f"🔁 Перенос SL → БУ на {be} по плану {plan.get('plan_id')}")
            if not DRY_RUN and self.bitget_trader:
                try:
                    self.bitget_trader.modify_stop(plan["side"], new_stop_price=be)
                    print(f"✅ SL перенесен в БУ на {be}")
                except Exception as e:
                    print(f"❌ Ошибка переноса SL в БУ: {e}")

        self.watcher = Watcher(get_now_price=self._get_now_price, on_breakeven=on_breakeven, poll_interval_sec=3)
        # запускаем watcher в фоне
        asyncio.create_task(self.watcher.start())

        self.signal_manager.load_signals()

        # 4) Резолв двух каналов (приватные: по ссылке или названию)
        await self._resolve_channels()

        print("🎉 Бот готов к работе!")

    def _get_now_price(self) -> float:
        # DRY_RUN: синтетическое движение цены к TP
        if DRY_RUN:
            if self._synthetic_price is None:
                # стартовая точка — средний entry или 30000
                self._synthetic_price = 30000.0
            # двигаем цену на каждом запросе (упрощённо):
            self._synthetic_price += 50.0  # для LONG растёт; для SHORT можно убывать — не критично для теста
            return self._synthetic_price
        # Реальный режим — можно кешировать последнюю цену из отдельной задачи
        # Для простоты вернём entry последнего плана, если нет цены
        return self._synthetic_price or 30000.0

    async def _resolve_by_link_or_name(self, link: str, name_substr: str) -> Optional[Channel]:
        # 4.1 сначала пробуем ссылку (invite)
        if link:
            try:
                ent = await self.client.get_entity(link)
                if isinstance(ent, Channel):
                    return ent
            except Exception as e:
                print(f"⚠️ Не удалось получить канал по ссылке {link}: {e}")
        # 4.2 затем ищем по подстроке названия среди твоих диалогов
        if name_substr:
            async for dialog in self.client.iter_dialogs():
                if isinstance(dialog.entity, Channel):
                    if name_substr.lower() in (dialog.name or "").lower():
                        return dialog.entity
        return None

    async def _resolve_channels(self):
        print("📡 Поиск каналов...")

        scalping = await self._resolve_by_link_or_name(SCALPING_LINK, SCALPING_NAME)
        intraday = await self._resolve_by_link_or_name(INTRADAY_LINK, INTRADAY_NAME)

        if not scalping:
            raise RuntimeError("Не найден SCALPING-канал (проверь TG_SOURCE_SCALPING_LINK или TG_SOURCE_SCALPING_NAME)")
        if not intraday:
            raise RuntimeError("Не найден INTRADAY-канал (проверь TG_SOURCE_INTRADAY_LINK или TG_SOURCE_INTRADAY_NAME)")

        self.channel_entities["SCALPING"] = scalping
        self.channel_entities["INTRADAY"] = intraday
        self.channel_source_by_id[scalping.id] = "SCALPING"
        self.channel_source_by_id[intraday.id] = "INTRADAY"

        print(f"✅ Найден SCALPING: id={scalping.id}, title={scalping.title}")
        print(f"✅ Найден INTRADAY: id={intraday.id}, title={intraday.title}")

    def setup_message_handlers(self):
        targets = list(self.channel_entities.values())

        @self.client.on(events.NewMessage(chats=targets))
        async def handle_new_message(event):
            await self._process_message(event)

    async def _process_message(self, event):
        try:
            message = event.message
            channel = await event.get_chat()
            channel_name = getattr(channel, 'title', str(channel.id))
            source = self.channel_source_by_id.get(channel.id, "INTRADAY")  # дефолт пусть будет интрадей

            text = message.text or ""
            if not text.strip():
                return

            # 5) фильтруем не-сигналы — пусть решает улучшенный парсер
            if not self.parser.is_trading_signal(text):
                return

            print(f"\n🎯 Новый сигнал [{source}] из канала {channel_name}:")
            print(f"   Текст: {text[:120].replace(os.linesep,' ')}{'...' if len(text)>120 else ''}")

            # Парсим сигнал
            signal = self.parser.parse_signal(
                message_id=str(message.id),
                channel_name=channel_name,
                text=text,
                timestamp=message.date.isoformat()
            )
            if not signal:
                print("   ❌ Не удалось распарсить сигнал")
                return

            # (опционально) проставим source внутрь сигнала, если у твоего dataclass есть такое поле
            if hasattr(signal, "source"):
                setattr(signal, "source", source)

            self._print_signal_info(signal)

            # Сохраняем
            self.signal_manager.add_signal(signal)

            # 6) Выполняем (с учётом деления депозита)
            await self._execute_signal(signal, source)

            self.stats['signals_processed'] += 1

        except Exception as e:
            print(f"❌ Ошибка обработки сообщения: {e}")

    def _print_signal_info(self, signal: TradingSignal):
        print("   📊 Параметры сигнала:")
        print(f"      Тип: {signal.position_type}")
        print(f"      Вход: {signal.entry_price}")
        print(f"      Стоп: {signal.stop_loss}")
        tps = getattr(signal, 'take_profits', []) or []
        print(f"      Цели: {tps[:3] if tps else 'Нет'}{'...' if len(tps)>3 else ''}")
        print(f"      Риск: {getattr(signal, 'risk_percent', None)}")
        print(f"      Плечо: {getattr(signal, 'leverage', None)}")

    async def _execute_signal(self, signal: TradingSignal, source: str):
        print("   🔄 Обработка сигнала...")

        # 1) делим депозит на поддепозиты
        equity_total = EQUITY_USDT
        if source == "SCALPING":
            equity_sub = equity_total * SPLIT_SCALPING_PCT / 100.0
        else:
            equity_sub = equity_total * SPLIT_INTRADAY_PCT / 100.0

        # 2) DRY_RUN режим: показываем подробный план и создаём демо-сделку
        if DRY_RUN:
            execu = Executor(self.bitget_trader, dry_run=True)
            plan = execu.plan_from_signal(signal, context={
                "source": source,
                "equity_sub": equity_sub,
                "risk_total_pct": RISK_TOTAL_CAP_PCT,
                "risk_leg_pct": RISK_LEG_PCT,
                "leverage_min": LEVERAGE_MIN,
                "breakeven_after_tp": BREAKEVEN_AFTER_TP
            })
            orders, plan_dict = execu.place_all(plan)
            print("   ✅ DRY_RUN: план составлен и ордера показаны")
            
            # Регистрируем план в watcher
            if self.watcher:
                self.watcher.register_plan(plan_dict)
            
            self._save_demo_trade(signal)
            return

        # 3) Реальная торговля
        if not self.bitget_trader:
            print("   ❌ Bitget трейдер не подключен")
            return

        try:
            # Создаем план для получения qty_total и tp_shares
            execu = Executor(self.bitget_trader, dry_run=False)
            plan = execu.plan_from_signal(signal, context={
                "source": source,
                "equity_sub": equity_sub,
                "risk_total_pct": RISK_TOTAL_CAP_PCT,
                "risk_leg_pct": RISK_LEG_PCT,
                "leverage_min": LEVERAGE_MIN,
                "breakeven_after_tp": BREAKEVEN_AFTER_TP
            })
            
            # Передаем рассчитанные параметры в execute_trade
            ctx = {
                "source": source,
                "equity_sub": equity_sub,
                "risk_total_pct": RISK_TOTAL_CAP_PCT,
                "risk_leg_pct": RISK_LEG_PCT,
                "leverage_min": LEVERAGE_MIN,
                "leverage_max": LEVERAGE_MAX,
                "breakeven_after_tp": BREAKEVEN_AFTER_TP,
                "qty_total": plan.leg1.qty + (plan.leg2.qty if plan.leg2 else 0.0),
                "tp_shares": plan.tp_shares,
            }
            
            result = self.bitget_trader.execute_trade(signal, context=ctx)
            
            if result:
                print("   ✅ Ордер(а) размещены")
                self.stats['signals_executed'] += 1
                
                # Регистрируем план в watcher для реальной торговли
                if self.watcher:
                    plan_dict = {
                        'symbol': plan.symbol,
                        'side': plan.side,
                        'entry': plan.entry_price,
                        'stop': plan.sl_price,
                        'tps': plan.tp_levels,
                        'tp_shares': plan.tp_shares,
                        'breakeven_after_tp': plan.move_sl_to_be_after_tp,
                        'plan_id': getattr(plan, 'plan_id', None),
                        'qty_total': plan.leg1.qty + (plan.leg2.qty if plan.leg2 else 0.0)
                    }
                    self.watcher.register_plan(plan_dict)
            else:
                print("   ❌ Ошибка размещения ордеров")
        except Exception as e:
            print(f"   ❌ Ошибка выполнения сигнала: {e}")

    def _save_demo_trade(self, signal: TradingSignal):
        try:
            demo_trade = {
                'trade_id': f"demo_{signal.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'signal_id': signal.message_id,
                'channel': signal.channel_name,
                'symbol': 'BTCUSDT',
                'side': signal.position_type,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': (signal.take_profits or [None])[0],
                'position_size': None,  # реальный размер посчитает risk-менеджер (когда подключим)
                'leverage': getattr(signal, 'leverage', None),
                'risk_percent': getattr(signal, 'risk_percent', None),
                'status': 'OPEN',
                'open_time': signal.timestamp,
                'pnl': 0.0,
                'pnl_percent': 0.0,
                'raw_signal': (signal.raw_text or '')[:200] + "..."
            }

            demo_trades = []
            if os.path.exists('demo_trades.json'):
                with open('demo_trades.json', 'r', encoding='utf-8') as f:
                    demo_trades = json.load(f)

            demo_trades.append(demo_trade)

            with open('demo_trades.json', 'w', encoding='utf-8') as f:
                json.dump(demo_trades, f, ensure_ascii=False, indent=2)

            print(f"   📁 Демо-сделка сохранена: {demo_trade['trade_id']}")
        except Exception as e:
            print(f"   ❌ Ошибка сохранения демо-сделки: {e}")

    def show_statistics(self):
        print("\n📊 Статистика работы бота:")
        print(f"   Время работы: {datetime.now() - self.stats['start_time']}")
        print(f"   Обработано сигналов: {self.stats['signals_processed']}")
        print(f"   Выполнено ордеров: {self.stats['signals_executed']}")
        print(f"   Общая прибыль: {self.stats['total_profit']:.2f} USDT")

    async def run(self):
        try:
            await self.initialize()
            self.setup_message_handlers()

            print("\n🎯 Бот слушает каналы:")
            for k, v in self.channel_entities.items():
                print(f"   - {k}: {getattr(v, 'title', v.id)}")

            print(f"\n💡 Режим: {'DRY_RUN (симуляция)' if DRY_RUN else 'РЕАЛЬНАЯ ТОРГОВЛЯ'}")
            print("   Для остановки: Ctrl+C")

            # Запускаем обе корутины параллельно
            tasks = [
                self.client.run_until_disconnected(),   # Telethon listener
                start_control_bot()                     # aiogram control bot
            ]
            await asyncio.gather(*tasks)

        except KeyboardInterrupt:
            print("\n⏹️ Остановка бота...")
            self.show_statistics()
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
        finally:
            if self.client:
                await self.client.disconnect()


class SignalManager:
    def __init__(self, filename: str = 'signals_history.json'):
        self.filename = filename
        self.signals: list[TradingSignal] = []

    def load_signals(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    self.signals.append(TradingSignal(
                        message_id=item['message_id'],
                        channel_name=item['channel_name'],
                        position_type=item['position_type'],
                        entry_price=item.get('entry_price'),
                        stop_loss=item.get('stop_loss'),
                        take_profits=item.get('take_profits', []),
                        risk_percent=item.get('risk_percent'),
                        leverage=item.get('leverage'),
                        timestamp=item.get('timestamp'),
                        raw_text=item.get('raw_text', '')
                    ))
                print(f"✅ Загружено {len(self.signals)} сигналов из истории")
        except Exception as e:
            print(f"❌ Ошибка загрузки истории сигналов: {e}")

    def add_signal(self, signal: TradingSignal):
        for s in self.signals:
            if s.message_id == signal.message_id and s.channel_name == signal.channel_name:
                return False
        self.signals.append(signal)
        self.save_signals()
        return True

    def save_signals(self):
        try:
            data = []
            for s in self.signals:
                data.append({
                    'message_id': s.message_id,
                    'channel_name': s.channel_name,
                    'position_type': s.position_type,
                    'entry_price': s.entry_price,
                    'stop_loss': s.stop_loss,
                    'take_profits': s.take_profits,
                    'risk_percent': s.risk_percent,
                    'leverage': s.leverage,
                    'timestamp': s.timestamp,
                    'raw_text': s.raw_text
                })
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения сигналов: {e}")


async def main():
    print("🤖 Запуск улучшенного торгового бота")
    print("=" * 60)
    bot = ImprovedTradingBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
