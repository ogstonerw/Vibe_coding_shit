# bot/tg_control.py
import os, json
from typing import List, Dict, Any
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command

from dotenv import load_dotenv
load_dotenv()

TGBOT_TOKEN = os.getenv("TGBOT_TOKEN", "")

# Support TG_OWNER_IDS (comma separated) or single TG_OWNER_ID
_owners_raw = os.getenv("TG_OWNER_IDS", os.getenv("TG_OWNER_ID", "")) or ""
def _parse_owner_ids(raw: str):
    ids = []
    for p in raw.split(','):
        p = p.strip()
        if not p:
            continue
        try:
            ids.append(int(p))
        except ValueError:
            # ignore non-integer entries
            continue
    return ids

ALLOWED_USERS = _parse_owner_ids(_owners_raw)



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
    if not TGBOT_TOKEN:
        print("[tg_control] TGBOT_TOKEN не задан — бот управления не будет запущен.")
        return
    if not ALLOWED_USERS:
        print("[tg_control] TG_OWNER_IDS/TG_OWNER_ID не настроены — бот запустится, но команды будут закрыты для всех.")

    from aiogram.client.default import DefaultBotProperties
    bot = Bot(TGBOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # debug toggle state
    _debug_state = {'core_signal_reader_debug': False}

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
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
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
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
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
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
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
        if ALLOWED_USERS and cb.from_user.id not in ALLOWED_USERS:
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
        if ALLOWED_USERS and cb.from_user.id not in ALLOWED_USERS:
            await cb.answer("Нет доступа", show_alert=True)
            return
        await cb.answer()
        await cmd_help(cb.message)  # переиспользуем

    @dp.message(Command("equity"))
    async def cmd_equity(message: Message):
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
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
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
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
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        _state["DRY_RUN"] = True
        await message.answer("✅ DRY_RUN включён (симуляция).")

    @dp.message(Command("dryrun_off"))
    async def cmd_dryrun_off(message: Message):
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        _state["DRY_RUN"] = False
        await message.answer("⚠️ DRY_RUN выключен. Реальные ордера будут отправляться, если включено в ядре.")

    @dp.message(Command("debug"))
    async def cmd_debug(message: Message):
        # toggle core.signal_reader logger
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
            await message.answer("❌ У вас нет доступа")
            return
        import logging as _logging
        lg = _logging.getLogger('core.signal_reader')
        current = _debug_state['core_signal_reader_debug']
        if current:
            lg.setLevel(_logging.INFO)
            _debug_state['core_signal_reader_debug'] = False
            await message.answer('DEBUG=OFF')
        else:
            lg.setLevel(_logging.DEBUG)
            _debug_state['core_signal_reader_debug'] = True
            await message.answer('DEBUG=ON')

    print("[tg_control] Bot control starting (aiogram). Allowed users:", ALLOWED_USERS)
    await dp.start_polling(bot)
