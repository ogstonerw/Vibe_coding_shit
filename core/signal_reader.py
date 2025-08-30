#!/usr/bin/env python3
"""Core: Telethon-based signal reader (user-bot) — read-only, uses session file.

This module intentionally will NOT perform interactive login. If the provided
session file is not already authorized, the reader will log and exit to avoid
triggering new logins that could disturb the owner's account.
"""
import os
import json
import logging
from typing import List

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import Channel

from improved_signal_parser import ImprovedSignalParser, TradingSignal
from trader.executor import Executor
from bitget_integration import BitgetTrader, load_bitget_config

log = logging.getLogger("core.signal_reader")
logging.basicConfig(level=logging.INFO)

# Ensure .env is loaded if main didn't do it
try:
    load_dotenv()
except Exception:
    pass

# Environment
API_ID = int(os.getenv('API_ID') or 0)
API_HASH = os.getenv('API_HASH') or ''
TG_SESSION = os.path.abspath(os.getenv('TG_SESSION', 'signal_trader'))
LOG_MSG_SESSION_ONLY = "Session-only mode: interactive login is disabled. If session is not authorized, the reader will exit."
SCALPING_LINK = os.getenv('TG_SOURCE_SCALPING_LINK') or ''
INTRADAY_LINK = os.getenv('TG_SOURCE_INTRADAY_LINK') or ''
DRY_RUN = (os.getenv('DRY_RUN', 'true').lower() == 'true')


class SignalManager:
    def __init__(self, filename: str = 'signals_history.json'):
        self.filename = filename
        self.signals = []

    def load_signals(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.signals = data
                log.info('Loaded %d signals from %s', len(self.signals), self.filename)
        except Exception as e:
            log.warning('Failed to load signals history: %s', e)

    def add_signal(self, signal: TradingSignal):
        # naive dedupe by message_id + channel_name
        for s in self.signals:
            if s.get('message_id') == signal.message_id and s.get('channel_name') == signal.channel_name:
                return False
        self.signals.append({
            'message_id': signal.message_id,
            'channel_name': signal.channel_name,
            'position_type': signal.position_type,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profits': getattr(signal, 'take_profits', []),
            'risk_percent': getattr(signal, 'risk_percent', None),
            'leverage': getattr(signal, 'leverage', None),
            'timestamp': getattr(signal, 'timestamp', None),
            'raw_text': getattr(signal, 'raw_text', '')
        })
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.signals, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning('Failed to save signals history: %s', e)
        return True


async def start_signal_reader():
    """Start Telethon client in read-only, non-interactive mode.

    If API_ID/API_HASH or session is missing or unauthorized, the coroutine will
    exit cleanly (no interactive login).
    """
    if not API_ID or not API_HASH:
        log.error('API_ID/API_HASH not set — signal reader will not start')
        return

    client = TelegramClient(TG_SESSION, API_ID, API_HASH)

    print(LOG_MSG_SESSION_ONLY)
    log.info('Using Telethon session path: %s', TG_SESSION)
    try:
        await client.connect()
    except Exception as e:
        log.exception('Failed to connect Telethon client: %s', e)
        return

    try:
        authorized = await client.is_user_authorized()
    except Exception as e:
        log.exception('Error checking authorization: %s', e)
        authorized = False

    if not authorized:
        log.error('Telethon session "%s" is NOT authorized. Aborting reader to avoid interactive login.', TG_SESSION)
        await client.disconnect()
        return

    log.info('Telethon session authorized — reader started (session=%s)', TG_SESSION)

    # Resolve channels
    watch_chats: List[Channel] = []
    for link in (SCALPING_LINK, INTRADAY_LINK):
        if not link:
            continue
        try:
            ent = await client.get_entity(link)
            if isinstance(ent, Channel):
                watch_chats.append(ent)
                log.info('Watching channel %s (id=%s)', getattr(ent, 'title', str(ent)), getattr(ent, 'id', ''))
        except Exception as e:
            log.warning('Cannot resolve channel %s: %s', link, e)

    if not watch_chats:
        log.warning('No channels configured for signal reader (TG_SOURCE_SCALPING_LINK / TG_SOURCE_INTRADAY_LINK)')
        await client.disconnect()
        return

    parser = ImprovedSignalParser()
    signal_manager = SignalManager()
    signal_manager.load_signals()

    # Bitget trader if configured and not in DRY_RUN
    bitget_trader = None
    if not DRY_RUN:
        try:
            cfg = load_bitget_config()
            if cfg:
                bitget_trader = BitgetTrader(cfg)
                log.info('Connected to Bitget')
        except Exception as e:
            log.warning('Failed to init BitgetTrader: %s', e)

    @client.on(events.NewMessage(chats=watch_chats))
    async def _handler(event):
        try:
            msg = event.message
            chat = await event.get_chat()
            text = msg.text or ''
            if not text.strip():
                return
            # Diagnostics: log message length and source
            source = 'INTRADAY'
            for ch in watch_chats:
                if getattr(ch, 'id', None) == getattr(chat, 'id', None):
                    source = 'SCALPING' if ch == watch_chats[0] else 'INTRADAY'
                    break
            log.info('[MSG] channel=%s message_id=%s len=%d source=%s', getattr(chat,'title',str(chat.id)), msg.id, len(text), source)

            is_sig, reason = parser.is_trading_signal(text)
            if not is_sig:
                log.info('Filtered out: not a trading signal (%s)', reason or 'unknown')
                return

            signal = parser.parse_signal(
                message_id=str(msg.id),
                channel_name=getattr(chat, 'title', str(chat.id)),
                text=text,
                timestamp=getattr(msg, 'date', None).isoformat() if getattr(msg, 'date', None) else None
            )
            if not signal:
                log.info('Parser returned no signal for message %s', msg.id)
                return

            # Log parsed fields
            try:
                tps = (signal.take_profits or [])[:3]
            except Exception:
                tps = []
            log.info('Parsed signal: side=%s entry=%s stop=%s tps=%s risk=%s leverage=%s source=%s',
                     getattr(signal,'position_type',None),
                     getattr(signal,'entry_price',None),
                     getattr(signal,'stop_loss',None),
                     tps,
                     getattr(signal,'risk_percent',None),
                     getattr(signal,'leverage',None),
                     source)

            # Warn on missing key fields
            if not getattr(signal,'stop_loss', None):
                log.warning('Parsed signal missing stop_loss for message %s', msg.id)

            # Save to history
            signal_manager.add_signal(signal)

            # DRY_RUN -> plan and write demo trade
            if DRY_RUN:
                execu = Executor(bitget_trader, dry_run=True)
                plan = execu.plan_from_signal(signal, context={})
                orders, plan_dict = execu.place_all(plan)
                log.info('DRY_RUN plan created for signal %s', signal.message_id)
                # save minimal demo trade
                try:
                    demo_path = 'demo_trades.json'
                    demo_trades = []
                    if os.path.exists(demo_path):
                        with open(demo_path, 'r', encoding='utf-8') as f:
                            demo_trades = json.load(f)
                    demo_trades.append({
                        'trade_id': f"demo_{signal.message_id}",
                        'signal_id': signal.message_id,
                        'channel': signal.channel_name,
                        'symbol': getattr(plan, 'symbol', 'unknown'),
                        'side': getattr(plan, 'side', ''),
                        'entry_price': getattr(plan, 'entry_price', None),
                        'status': 'OPEN'
                    })
                    with open(demo_path, 'w', encoding='utf-8') as f:
                        json.dump(demo_trades, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    log.warning('Failed to save demo trade: %s', e)
            else:
                # Real trading path (delegated to Executor / BitgetTrader)
                try:
                    execu = Executor(bitget_trader, dry_run=False)
                    plan = execu.plan_from_signal(signal, context={})
                    result = bitget_trader.execute_trade(signal, context={'plan': plan}) if bitget_trader else None
                    log.info('Executed trade for signal %s: %s', signal.message_id, bool(result))
                except Exception as e:
                    log.exception('Error executing real trade: %s', e)

        except Exception as e:
            log.exception('Error handling message event: %s', e)

    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
