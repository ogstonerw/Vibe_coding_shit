#!/usr/bin/env python3
"""Offline signal parser + executor plan tester.

Usage:
  python scripts/paste_signal.py "text of signal"
  or
  python scripts/paste_signal.py -f file.txt

Reads input, runs ImprovedSignalParser.parse_signal and Executor.plan_from_signal(dry_run=True), prints JSON.
"""
import sys, os, json
from dotenv import load_dotenv
load_dotenv()

from improved_signal_parser import ImprovedSignalParser, TradingSignal
from trader.executor import Executor

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
        plan = execu.plan_from_signal(sig, context={'source':'OFFLINE'})
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
