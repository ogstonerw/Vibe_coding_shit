# bot/views.py
from typing import Dict, Any, List
from datetime import datetime

def format_positions_list(position: Dict[str, Any]) -> str:
    """Форматирование позиции для списка"""
    symbol = position.get('symbol', 'N/A')
    side = position.get('side', 'N/A')
    state = position.get('state', 'N/A')
    created_at = position.get('created_at', '')
    
    # Форматируем дату
    try:
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        date_str = dt.strftime('%d.%m %H:%M')
    except:
        date_str = created_at[:16]
    
    # Эмодзи для стороны
    side_emoji = "🟢" if side == "BUY" else "🔴"
    
    # Эмодзи для состояния
    state_emoji = {
        'PENDING_SETUP': '⏳',
        'LEG1_PLACED': '📝',
        'LEG1_FILLED': '✅',
        'TP1_HIT': '🎯',
        'TP2_HIT': '🎯',
        'BREAKEVEN': '⚖️',
        'CLOSED': '🔒',
        'CANCELLED': '❌',
        'STOPPED_OUT': '🛑'
    }.get(state, '❓')
    
    return f"{side_emoji} {symbol} {side} {state_emoji} {state} | {date_str}"

def format_position_details(position: Dict[str, Any], orders: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
    """Форматирование деталей позиции"""
    text = f"""
📊 Детали позиции #{position.get('id', 'N/A')}

🔸 Символ: {position.get('symbol', 'N/A')}
🔸 Сторона: {position.get('side', 'N/A')}
🔸 Состояние: {position.get('state', 'N/A')}
🔸 Источник: {position.get('source', 'N/A')}

💰 Цены:
• Вход: {position.get('entry_low', 0):.2f} - {position.get('entry_high', 0):.2f}
• Стоп: {position.get('stop_price', 0):.2f}

📈 Риск:
• Нога: {position.get('risk_leg_pct', 0):.1f}%
• Общий: {position.get('risk_total_cap_pct', 0):.1f}%
• Плечо: {position.get('leverage_min', 0)}x - {position.get('leverage_max', 0)}x

📅 Время:
• Создана: {format_datetime(position.get('created_at', ''))}
• Обновлена: {format_datetime(position.get('updated_at', ''))}
"""
    
    # Добавляем ордера
    if orders:
        text += "\n📋 Ордера:\n"
        for order in orders:
            order_text = format_order(order)
            text += f"• {order_text}\n"
    
    # Добавляем статистику
    if stats:
        text += f"""
📊 Результат:
• P&L: {stats.get('pnl_usdt', 0):.2f} USDT ({stats.get('pnl_pct', 0):.2f}%)
• Результат: {'✅ Выигрыш' if stats.get('win', 0) else '❌ Проигрыш'}
• Причина закрытия: {stats.get('closed_reason', 'N/A')}
"""
    
    return text

def format_order(order: Dict[str, Any]) -> str:
    """Форматирование ордера"""
    kind = order.get('kind', 'N/A')
    side = order.get('side', 'N/A')
    price = order.get('price', 0)
    qty = order.get('qty', 0)
    status = order.get('status', 'N/A')
    
    # Эмодзи для типа ордера
    kind_emoji = {
        'ENTRY': '📥',
        'TP': '🎯',
        'SL': '🛑'
    }.get(kind, '❓')
    
    # Эмодзи для статуса
    status_emoji = {
        'NEW': '⏳',
        'FILLED': '✅',
        'CANCELED': '❌'
    }.get(status, '❓')
    
    return f"{kind_emoji} {kind} {side} @ {price:.2f} x {qty:.4f} {status_emoji} {status}"

def format_statistics(stats: Dict[str, Any], recent_performance: List[Dict[str, Any]]) -> str:
    """Форматирование статистики"""
    text = f"""
📊 Общая статистика

📈 Сделки:
• Всего: {stats.get('total_trades', 0)}
• Выигрышных: {stats.get('wins', 0)}
• Проигрышных: {stats.get('losses', 0)}
• Винрейт: {stats.get('win_rate', 0):.1f}%

💰 P&L:
• Общий: {stats.get('total_pnl', 0):.2f} USDT
• Средний: {stats.get('avg_pnl_pct', 0):.2f}%
• Выигрыши: {stats.get('total_wins', 0):.2f} USDT
• Проигрыши: {stats.get('total_losses', 0):.2f} USDT
"""
    
    # Добавляем производительность за последние дни
    if recent_performance:
        text += "\n📅 Последние 7 дней:\n"
        for day in recent_performance[:7]:
            date = day.get('date', 'N/A')
            trades = day.get('trades', 0)
            wins = day.get('wins', 0)
            pnl = day.get('daily_pnl', 0)
            
            win_rate = (wins / trades * 100) if trades > 0 else 0
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            text += f"• {date}: {trades} сделок, {win_rate:.0f}% винрейт, {pnl_emoji} {pnl:.2f} USDT\n"
    
    return text

def format_datetime(dt_str: str) -> str:
    """Форматирование даты и времени"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M:%S')
    except:
        return dt_str[:19] if dt_str else 'N/A'

def format_error_message(error: str) -> str:
    """Форматирование сообщения об ошибке"""
    return f"❌ Ошибка: {error}"

def format_success_message(message: str) -> str:
    """Форматирование сообщения об успехе"""
    return f"✅ {message}"

def format_warning_message(message: str) -> str:
    """Форматирование предупреждения"""
    return f"⚠️ {message}"
