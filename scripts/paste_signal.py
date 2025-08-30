#!/usr/bin/env python3
"""Offline signal parser + executor plan tester.

Usage:
  python scripts/paste_signal.py "text of signal"
  or
  python scripts/paste_signal.py -f file.txt

Reads input, runs ImprovedSignalParser.parse_signal and Executor.plan_from_signal(dry_run=True), prints JSON.
"""
import sys, os, json
# ensure project root is on sys.path when running from scripts/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from improved_signal_parser import ImprovedSignalParser, TradingSignal
from trader.executor import Executor
from nlp import parser_rules
from types import SimpleNamespace
import re

parser = ImprovedSignalParser()

def read_input():
    if len(sys.argv) >= 3 and sys.argv[1] in ('-f','--file'):
        with open(sys.argv[2], 'r', encoding='utf-8') as f:
            return f.read()
    elif len(sys.argv) >= 2:
        return sys.argv[1]
    else:
        print('Provide signal text as argument or use -f file')
        sys.exit(2)

if __name__ == '__main__':
    text = read_input()
    sig = parser.parse_signal(message_id='offline_1', channel_name='offline', text=text, timestamp=None)
    print('\n=== Parsed signal ===')
    print(json.dumps(sig.__dict__ if sig else {'parsed': None}, indent=2, ensure_ascii=False))
    if not sig:
        print('\nNo parsed signal')
        sys.exit(0)

    execu = Executor(None, dry_run=True)
    try:
        # Try project's nlp parser first (preferred). If it fails, synthesize a minimal parsed object
        parsed = None
        try:
            parsed = parser_rules.parser.parse(text)
        except Exception:
            parsed = None

        if not parsed:
            # synthesize object expected by Executor when parse() returns None
            # Executor will take attributes from the signal object in the fallback branch
            # Map LONG->BUY, SHORT->SELL
            side = 'BUY' if getattr(sig, 'position_type', '').upper().startswith('LONG') else 'SELL'
            entry_low = entry_high = 0.0
            ep = getattr(sig, 'entry_price', None)
            if ep and isinstance(ep, str) and '-' in ep:
                parts = ep.split('-')[:2]
                try:
                    entry_low = float(parts[0])
                    entry_high = float(parts[1])
                except Exception:
                    entry_low = entry_high = 0.0
            else:
                try:
                    entry_low = entry_high = float(ep)
                except Exception:
                    entry_low = entry_high = 0.0

            # If we still don't have entry prices, try to regex-extract from raw text
            if entry_low == 0.0 and entry_high == 0.0:
                # look for range like 112300-111500 or 112300 - 111500
                m = re.search(r"(\d+[\.,]?\d*)\s*[-–—]\s*(\d+[\.,]?\d*)", text)
                if m:
                    try:
                        entry_low = float(m.group(1).replace(',', '.'))
                        entry_high = float(m.group(2).replace(',', '.'))
                    except Exception:
                        entry_low = entry_high = 0.0

            try:
                stop_loss = float(getattr(sig, 'stop_loss', 0) or 0)
            except Exception:
                stop_loss = 0.0

            # If stop_loss missing, try regex like SL 110800 or stop 110800
            if not stop_loss:
                m = re.search(r"(?:SL|STOP)[:\s]*([0-9]+(?:[\.,][0-9]+)?)", text, flags=re.IGNORECASE)
                if m:
                    try:
                        stop_loss = float(m.group(1).replace(',', '.'))
                    except Exception:
                        stop_loss = 0.0

            tp_list = []
            for t in (getattr(sig, 'take_profits', []) or []):
                try:
                    tp_list.append(float(t))
                except Exception:
                    pass

            # If no TPs, try to extract after TP or TP: pattern
            if not tp_list:
                m = re.search(r"TP[s]?[:\s]*([0-9,\s\.]+)", text, flags=re.IGNORECASE)
                if m:
                    raw = m.group(1)
                    for part in re.split(r"[,\s]+", raw):
                        try:
                            if part.strip():
                                tp_list.append(float(part.replace(',', '.')))
                        except Exception:
                            pass

            fallback = SimpleNamespace(
                direction=side,
                entry_low=entry_low,
                entry_high=entry_high,
                stop_loss=stop_loss,
                take_profit=(tp_list[0] if tp_list else None),
                take_profit2=(tp_list[1] if len(tp_list)>1 else None)
            )
            plan = execu.plan_from_signal(fallback, context={'source':'OFFLINE'})
        else:
            # parsed is the nlp.parser_rules.ParsedSignal-like object
            plan = execu.plan_from_signal(parsed, context={'source':'OFFLINE'})
        print('\n=== Plan ===')
        # Simplified plan representation
        pd = {
            'symbol': getattr(plan,'symbol',None),
            'entry': getattr(plan,'entry_price',None) or getattr(plan,'entry_zone',None),
            'stop': getattr(plan,'sl_price',None),
            'tps': getattr(plan,'tp_levels',None),
            'tp_shares': getattr(plan,'tp_shares',None),
            'qty_total': (getattr(plan,'leg1',None).qty + (getattr(plan,'leg2',None).qty if getattr(plan,'leg2',None) else 0)) if getattr(plan,'leg1',None) else None
        }
        print(json.dumps(pd, indent=2, ensure_ascii=False))
    except Exception as e:
        print('Error creating plan:', e)
