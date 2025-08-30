-- Схема базы данных для торгового бота
-- SQLite миграции

-- Таблица позиций
CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id TEXT UNIQUE NOT NULL,              -- hash сообщения (канал+время+текст)
  source TEXT NOT NULL,                        -- SCALPING | INTRADAY
  symbol TEXT NOT NULL,                        -- BTCUSDT
  side TEXT NOT NULL,                          -- BUY | SELL
  entry_low REAL NOT NULL,
  entry_high REAL NOT NULL,
  stop_price REAL NOT NULL,
  risk_leg_pct REAL NOT NULL,                  -- 1.5
  risk_total_cap_pct REAL NOT NULL,            -- 3.0
  leverage_min INTEGER NOT NULL,
  leverage_max INTEGER NOT NULL,
  state TEXT NOT NULL,                         -- FSM: PENDING_SETUP, LEG1_PLACED, TP1_HIT, BREAKEVEN...
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Таблица ордеров
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  position_id INTEGER NOT NULL,
  kind TEXT NOT NULL,                          -- ENTRY | TP | SL
  side TEXT NOT NULL,                          -- BUY | SELL
  price REAL NOT NULL,
  qty REAL NOT NULL,
  reduce_only INTEGER NOT NULL DEFAULT 0,      -- 0/1
  status TEXT NOT NULL DEFAULT 'NEW',          -- NEW | FILLED | CANCELED
  order_id TEXT,                               -- ID ордера от биржи
  extra_json TEXT,                             -- Дополнительные данные в JSON
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(position_id) REFERENCES positions(id)
);

-- Таблица исполнений
CREATE TABLE IF NOT EXISTS fills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  position_id INTEGER NOT NULL,
  price REAL NOT NULL,
  qty REAL NOT NULL,
  fee REAL NOT NULL DEFAULT 0,
  ts TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(order_id) REFERENCES orders(id),
  FOREIGN KEY(position_id) REFERENCES positions(id)
);

-- Таблица статистики
CREATE TABLE IF NOT EXISTS stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  position_id INTEGER NOT NULL UNIQUE,
  pnl_usdt REAL NOT NULL DEFAULT 0,
  pnl_pct REAL NOT NULL DEFAULT 0,
  win INTEGER NOT NULL DEFAULT 0,              -- 0/1
  closed_reason TEXT,                          -- STOP | TP | TIMEOUT | MANUAL
  closed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(position_id) REFERENCES positions(id)
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_positions_signal_id ON positions(signal_id);
CREATE INDEX IF NOT EXISTS idx_positions_state ON positions(state);
CREATE INDEX IF NOT EXISTS idx_positions_source ON positions(source);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at);

CREATE INDEX IF NOT EXISTS idx_orders_position_id ON orders(position_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_kind ON orders(kind);

CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills(order_id);
CREATE INDEX IF NOT EXISTS idx_fills_position_id ON fills(position_id);

CREATE INDEX IF NOT EXISTS idx_stats_position_id ON stats(position_id);
CREATE INDEX IF NOT EXISTS idx_stats_win ON stats(win);
CREATE INDEX IF NOT EXISTS idx_stats_closed_at ON stats(closed_at);

-- Триггер для обновления updated_at
CREATE TRIGGER IF NOT EXISTS update_positions_updated_at 
  AFTER UPDATE ON positions
  BEGIN
    UPDATE positions SET updated_at = datetime('now') WHERE id = NEW.id;
  END;

CREATE TRIGGER IF NOT EXISTS update_orders_updated_at 
  AFTER UPDATE ON orders
  BEGIN
    UPDATE orders SET updated_at = datetime('now') WHERE id = NEW.id;
  END;
