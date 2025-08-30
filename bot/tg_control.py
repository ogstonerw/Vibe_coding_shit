# bot/tg_control.py
import os, json
from typing import List, Dict, Any
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

TGBOT_TOKEN = os.getenv("TGBOT_TOKEN", "")

# Обрабатываем TG_OWNER_ID - может быть числом или username
_owner_id_raw = os.getenv("TG_OWNER_ID", "0")
try:
    TG_OWNER_ID = int(_owner_id_raw)
except ValueError:
    print(f"[tg_control] TG_OWNER_ID '{_owner_id_raw}' не является числом. Используйте числовой ID.")
    TG_OWNER_ID = 0

# Обрабатываем TG_OWNER_ID_2 - второй аккаунт
_owner_id_2_raw = os.getenv("TG_OWNER_ID_2", "0")
try:
    TG_OWNER_ID_2 = int(_owner_id_2_raw)
except ValueError:
    print(f"[tg_control] TG_OWNER_ID_2 '{_owner_id_2_raw}' не является числом. Используйте числовой ID.")
    TG_OWNER_ID_2 = 0

# Список разрешенных пользователей
ALLOWED_USERS = [TG_OWNER_ID, TG_OWNER_ID_2]
ALLOWED_USERS = [uid for uid in ALLOWED_USERS if uid != 0]  # Убираем нулевые ID

print(f"[tg_control] Загружены разрешенные пользователи: {ALLOWED_USERS}")



def _load_demo_trades() -> List[Dict[str, Any]]:
    if os.path.exists("demo_trades.json"):
        with open("demo_trades.json","r",encoding="utf-8") as f:
            return json.load(f)
    return []

def _format_trade(tr: Dict[str,Any], idx: int, total: int) -> str:
    return (
        f"<b>Сделка {idx+1}/{total}</b>\n"
        f"ID: <code>{tr.get('trade_id')}</code>\n"
        f"Канал: {tr.get('channel')}\n"
        f"Символ: {tr.get('symbol')} | Сторона: {tr.get('side')}\n"
        f"Вход: {tr.get('entry_price')} | SL: {tr.get('stop_loss')} | TP: {tr.get('take_profit')}\n"
        f"Леверидж: {tr.get('leverage')} | Риск%: {tr.get('risk_percent')}\n"
        f"Статус: {tr.get('status')} | Открыта: {tr.get('open_time')}\n"
        f"PnL: {tr.get('pnl')} USDT ({tr.get('pnl_percent')}%)\n"
    )

def _nav_kb(idx: int, total: int) -> InlineKeyboardMarkup:
    prev_btn = InlineKeyboardButton(text="⬅️", callback_data=f"hist:{max(idx-1,0)}")
    next_btn = InlineKeyboardButton(text="➡️", callback_data=f"hist:{min(idx+1,total-1)}")
    help_btn = InlineKeyboardButton(text="ℹ️ Инструкции", callback_data="help")
    return InlineKeyboardMarkup(inline_keyboard=[[prev_btn, next_btn],[help_btn]])

async def start_control_bot(settings=None):
    """
    Запускает aiogram v3-бота управления.
    Требуются в .env: TGBOT_TOKEN, TG_OWNER_ID.
    Команды: /start, /help, /history, /equity, /stats, /dryrun_on, /dryrun_off
    """
    if not TGBOT_TOKEN or not ALLOWED_USERS:
        print("[tg_control] TGBOT_TOKEN или разрешенные пользователи не заданы — бот управления не будет запущен.")
        print(f"   Разрешенные пользователи: {ALLOWED_USERS}")
        return

    from aiogram.client.default import DefaultBotProperties
    bot = Bot(TGBOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # === Хранилище runtime-настроек (минимум) ===
    # Читаем DRY_RUN из env на старте; даём возможность переключать в рантайме
    _state = {
        "DRY_RUN": os.getenv("DRY_RUN","true").lower()=="true",
        "EQUITY_USDT": float(os.getenv("EQUITY_USDT","0")),
        "SPLIT_SCALPING_PCT": float(os.getenv("SPLIT_SCALPING_PCT","15")),
        "SPLIT_INTRADAY_PCT": float(os.getenv("SPLIT_INTRADAY_PCT","85")),
    }

    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        if message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        await message.answer(
            "Привет! Я бот управления трейдером.\n"
            "Команды:\n"
            "/history — последние 10 сделок (листание)\n"
            "/equity — текущая оценка депозита и сплиты 15%/85%\n"
            "/stats — краткая статистика\n"
            "/dryrun_on /dryrun_off — переключение симуляции\n"
            "/help — справка по командам"
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        if message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        users_info = f"Разрешенные пользователи: {len(ALLOWED_USERS)}"
        await message.answer(
            "ℹ️ Инструкции:\n"
            "<b>/history</b> — показать последние 10 сделок. Листай ⬅️➡️.\n"
            "<b>/equity</b> — показать текущий EQUITY и сплиты 15% (скальпинг) / 85% (интрадей).\n"
            "<b>/stats</b> — базовые счётчики (сколько сигналов, ордеров и т.п.).\n"
            "<b>/dryrun_on</b> / <b>/dryrun_off</b> — включить/выключить симуляцию.\n"
            f"Доступ: {users_info}"
        )

    @dp.message(Command("history"))
    async def cmd_history(message: Message):
        if message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        trades = _load_demo_trades()[-10:]
        if not trades:
            await message.answer("История пуста.")
            return
        idx = 0
        await message.answer(_format_trade(trades[idx], idx, len(trades)), reply_markup=_nav_kb(idx, len(trades)))

    @dp.callback_query(F.data.startswith("hist:"))
    async def cb_history(cb: CallbackQuery):
        if cb.from_user.id not in ALLOWED_USERS:
            await cb.answer("Нет доступа", show_alert=True)
            return
        trades = _load_demo_trades()[-10:]
        if not trades:
            await cb.answer("История пуста", show_alert=True)
            return
        idx = int(cb.data.split(":")[1])
        idx = max(0, min(idx, len(trades)-1))
        await cb.message.edit_text(_format_trade(trades[idx], idx, len(trades)), reply_markup=_nav_kb(idx, len(trades)))

    @dp.callback_query(F.data == "help")
    async def cb_help(cb: CallbackQuery):
        if cb.from_user.id not in ALLOWED_USERS:
            await cb.answer("Нет доступа", show_alert=True)
            return
        await cb.answer()
        await cmd_help(cb.message)  # переиспользуем

    @dp.message(Command("equity"))
    async def cmd_equity(message: Message):
        if message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        eq = _state["EQUITY_USDT"]
        s15 = _state["SPLIT_SCALPING_PCT"]
        s85 = _state["SPLIT_INTRADAY_PCT"]
        await message.answer(
            f"💰 EQUITY: <b>{eq:.2f} USDT</b>\n"
            f"Скальпинг: {s15:.1f}% → <b>{eq*s15/100:.2f} USDT</b>\n"
            f"Интрадей: {s85:.1f}% → <b>{eq*s85/100:.2f} USDT</b>"
        )

    @dp.message(Command("stats"))
    async def cmd_stats(message: Message):
        if message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        # Мини-версия: читаем размер demo_trades.json
        trades = _load_demo_trades()
        await message.answer(
            "📊 Статистика (демо):\n"
            f"Всего записей в истории: <b>{len(trades)}</b>\n"
            f"DRY_RUN: <b>{'ON' if _state['DRY_RUN'] else 'OFF'}</b>"
        )

    @dp.message(Command("dryrun_on"))
    async def cmd_dryrun_on(message: Message):
        if message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        _state["DRY_RUN"] = True
        await message.answer("✅ DRY_RUN включён (симуляция).")

    @dp.message(Command("dryrun_off"))
    async def cmd_dryrun_off(message: Message):
        if message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        _state["DRY_RUN"] = False
        await message.answer("⚠️ DRY_RUN выключен. Реальные ордера будут отправляться, если включено в ядре.")

    print("[tg_control] Бот управления запущен")
    await dp.start_polling(bot)
