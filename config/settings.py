import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

@dataclass
class TelegramConfig:
    api_id: str
    api_hash: str
    session_name: str
    source_scalping: str
    source_intraday: str
    bot_token: str
    owner_id: int

@dataclass
class BitgetConfig:
    api_key: str
    api_secret: str
    passphrase: str
    base_url: str
    market: str
    symbol: str

@dataclass
class RiskConfig:
    equity_usdt: float
    split_scalping_pct: float
    split_intraday_pct: float
    risk_leg_pct: float
    risk_total_cap_pct: float
    leverage_min: int
    leverage_max: int
    breakeven_after_tp: int
    time_stop_min: int

@dataclass
class BehaviorConfig:
    dry_run: bool
    log_level: str
    db_path: str

class Settings:
    def __init__(self):
        self.telegram = self._load_telegram_config()
        self.bitget = self._load_bitget_config()
        self.risk = self._load_risk_config()
        self.behavior = self._load_behavior_config()
        self._validate_config()

    def _load_telegram_config(self) -> TelegramConfig:
        return TelegramConfig(
            api_id=os.getenv('API_ID', ''),  # Используем API_ID из .env
            api_hash=os.getenv('API_HASH', ''),  # Используем API_HASH из .env
            session_name=os.getenv('TG_SESSION', 'signal_trader'),
            source_scalping=os.getenv('TG_SOURCE_SCALPING_NAME', 'Pentagon SCALPING'),  # Используем имя канала
            source_intraday=os.getenv('TG_SOURCE_INTRADAY_NAME', 'Pentagon INTRADAY'),  # Используем имя канала
            bot_token=os.getenv('TGBOT_TOKEN', ''),
            owner_id=int(os.getenv('TG_OWNER_ID', '0') or '0')
        )

    def _load_bitget_config(self) -> BitgetConfig:
        return BitgetConfig(
            api_key=os.getenv('BITGET_API_KEY', ''),
            api_secret=os.getenv('BITGET_API_SECRET', ''),
            passphrase=os.getenv('BITGET_PASSPHRASE', ''),
            base_url=os.getenv('BITGET_BASE', 'https://api.bitget.com'),
            market=os.getenv('MARKET', 'umcbl'),
            symbol=os.getenv('SYMBOL', 'BTCUSDT')
        )

    def _load_risk_config(self) -> RiskConfig:
        return RiskConfig(
            equity_usdt=float(os.getenv('EQUITY_USDT', '1000')),
            split_scalping_pct=float(os.getenv('SPLIT_SCALPING_PCT', '15')),
            split_intraday_pct=float(os.getenv('SPLIT_INTRADAY_PCT', '85')),
            risk_leg_pct=float(os.getenv('RISK_LEG_PCT', '1.5')),
            risk_total_cap_pct=float(os.getenv('RISK_TOTAL_CAP_PCT', '3.0')),
            leverage_min=int(os.getenv('LEVERAGE_MIN', '10')),
            leverage_max=int(os.getenv('LEVERAGE_MAX', '25')),
            breakeven_after_tp=int(os.getenv('BREAKEVEN_AFTER_TP', '2')),
            time_stop_min=int(os.getenv('TIME_STOP_MIN', '240'))
        )

    def _load_behavior_config(self) -> BehaviorConfig:
        return BehaviorConfig(
            dry_run=os.getenv('DRY_RUN', 'true').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            db_path=os.getenv('DB_PATH', 'storage/trader.db')
        )

    def _validate_config(self):
        """Валидация конфигурации"""
        errors = []
        
        # Проверка Telegram
        if not self.telegram.api_id:
            errors.append("TG_API_ID не установлен")
        if not self.telegram.api_hash:
            errors.append("TG_API_HASH не установлен")
        if not self.telegram.source_scalping:
            errors.append("TG_SOURCE_SCALPING не установлен")
        if not self.telegram.source_intraday:
            errors.append("TG_SOURCE_INTRADAY не установлен")
        if not self.telegram.bot_token:
            errors.append("TGBOT_TOKEN не установлен")
        if self.telegram.owner_id == 0:
            errors.append("TG_OWNER_ID не установлен")

        # Проверка Bitget
        if not self.behavior.dry_run:
            if not self.bitget.api_key:
                errors.append("BITGET_API_KEY не установлен")
            if not self.bitget.api_secret:
                errors.append("BITGET_API_SECRET не установлен")
            if not self.bitget.passphrase:
                errors.append("BITGET_PASSPHRASE не установлен")

        # Проверка рисков
        if self.risk.split_scalping_pct + self.risk.split_intraday_pct != 100:
            errors.append("SPLIT_SCALPING_PCT + SPLIT_INTRADAY_PCT должно равняться 100")
        if self.risk.risk_leg_pct <= 0 or self.risk.risk_total_cap_pct <= 0:
            errors.append("Риски должны быть положительными")
        if self.risk.leverage_min > self.risk.leverage_max:
            errors.append("LEVERAGE_MIN не может быть больше LEVERAGE_MAX")

        if errors:
            raise ValueError(f"Ошибки конфигурации: {'; '.join(errors)}")

# Глобальный экземпляр настроек
settings = Settings()
