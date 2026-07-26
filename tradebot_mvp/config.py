from __future__ import annotations

import hashlib
import json
import re
import stat
import tomllib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .contracts import Source, decimal_text


DECIMAL_RE = re.compile(r"(?:0|[1-9]\d{0,17})(?:\.\d{1,8})?\Z")
VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")

CONFIG_FIELDS = {
    "account_equity",
    "adverse_cost_per_unit",
    "classification",
    "config_version",
    "first_leg_risk",
    "intraday_allocation",
    "leverage",
    "max_active_setups",
    "mode",
    "price_tick",
    "quantity_step",
    "scalping_allocation",
    "scalping_channel_id",
    "intraday_channel_id",
}
MAX_CONFIG_BYTES = 64 * 1024


class ConfigError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class MvpConfig:
    config_version: str
    classification: str
    mode: str
    account_equity: Decimal
    leverage: int
    quantity_step: Decimal
    price_tick: Decimal
    adverse_cost_per_unit: Decimal
    scalping_allocation: Decimal
    intraday_allocation: Decimal
    scalping_channel_id: str
    intraday_channel_id: str
    first_leg_risk: Decimal
    max_active_setups: int
    fingerprint: str

    def allocation_for(self, source: Source) -> Decimal:
        if source is Source.SCALPING:
            return self.scalping_allocation
        return self.intraday_allocation

    def channel_for(self, source: Source) -> str:
        if source is Source.SCALPING:
            return self.scalping_channel_id
        return self.intraday_channel_id


def parse_decimal(value: Any, *, field: str, allow_zero: bool) -> Decimal:
    if type(value) is not str or not DECIMAL_RE.fullmatch(value):
        raise ConfigError(f"INVALID_DECIMAL:{field}")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:  # defensive; regex already limits grammar
        raise ConfigError(f"INVALID_DECIMAL:{field}") from exc
    if not parsed.is_finite() or parsed < 0 or (not allow_zero and parsed == 0):
        raise ConfigError(f"INVALID_DECIMAL:{field}")
    return parsed


def _expect_string(data: dict[str, Any], field: str) -> str:
    value = data[field]
    if type(value) is not str:
        raise ConfigError(f"INVALID_TYPE:{field}")
    return value


def _expect_integer(data: dict[str, Any], field: str) -> int:
    value = data[field]
    if type(value) is not int:
        raise ConfigError(f"INVALID_TYPE:{field}")
    return value


def _normalized_config_values(
    *,
    config_version: str,
    classification: str,
    mode: str,
    account_equity: Decimal,
    leverage: int,
    quantity_step: Decimal,
    price_tick: Decimal,
    adverse_cost_per_unit: Decimal,
    scalping_allocation: Decimal,
    intraday_allocation: Decimal,
    scalping_channel_id: str,
    intraday_channel_id: str,
    first_leg_risk: Decimal,
    max_active_setups: int,
) -> dict[str, str | int]:
    return {
        "account_equity": decimal_text(account_equity),
        "adverse_cost_per_unit": decimal_text(adverse_cost_per_unit),
        "classification": classification,
        "config_version": config_version,
        "first_leg_risk": decimal_text(first_leg_risk),
        "intraday_allocation": decimal_text(intraday_allocation),
        "intraday_channel_id": intraday_channel_id,
        "leverage": leverage,
        "max_active_setups": max_active_setups,
        "mode": mode,
        "price_tick": decimal_text(price_tick),
        "quantity_step": decimal_text(quantity_step),
        "scalping_allocation": decimal_text(scalping_allocation),
        "scalping_channel_id": scalping_channel_id,
    }


def config_from_mapping(data: Any) -> MvpConfig:
    if type(data) is not dict or set(data) != CONFIG_FIELDS:
        raise ConfigError("CONFIG_FIELDS_MISMATCH")
    if any(type(key) is not str for key in data):
        raise ConfigError("CONFIG_FIELDS_MISMATCH")

    config_version = _expect_string(data, "config_version")
    if not VERSION_RE.fullmatch(config_version):
        raise ConfigError("INVALID_CONFIG_VERSION")
    classification = _expect_string(data, "classification")
    mode = _expect_string(data, "mode")
    if classification != "TEST_FIXTURE_ONLY":
        raise ConfigError("CLASSIFICATION_NOT_TEST_ONLY")
    if mode != "OFFLINE_SIMULATION":
        raise ConfigError("MODE_NOT_OFFLINE_SIMULATION")

    account_equity = parse_decimal(data["account_equity"], field="account_equity", allow_zero=False)
    quantity_step = parse_decimal(data["quantity_step"], field="quantity_step", allow_zero=False)
    price_tick = parse_decimal(data["price_tick"], field="price_tick", allow_zero=False)
    adverse_cost = parse_decimal(
        data["adverse_cost_per_unit"],
        field="adverse_cost_per_unit",
        allow_zero=True,
    )
    scalping = parse_decimal(data["scalping_allocation"], field="scalping_allocation", allow_zero=False)
    intraday = parse_decimal(data["intraday_allocation"], field="intraday_allocation", allow_zero=False)
    first_leg = parse_decimal(data["first_leg_risk"], field="first_leg_risk", allow_zero=False)
    scalping_channel_id = _expect_string(data, "scalping_channel_id")
    intraday_channel_id = _expect_string(data, "intraday_channel_id")
    leverage = _expect_integer(data, "leverage")
    max_active = _expect_integer(data, "max_active_setups")

    if scalping != Decimal("0.15") or intraday != Decimal("0.85"):
        raise ConfigError("ALLOCATION_POLICY_MISMATCH")
    if first_leg != Decimal("0.015"):
        raise ConfigError("FIRST_LEG_POLICY_MISMATCH")
    if (
        not scalping_channel_id
        or not intraday_channel_id
        or len(scalping_channel_id) > 128
        or len(intraday_channel_id) > 128
        or scalping_channel_id == intraday_channel_id
    ):
        raise ConfigError("INVALID_CHANNEL_ALLOWLIST")
    if leverage < 10 or leverage > 25:
        raise ConfigError("LEVERAGE_OUT_OF_POLICY")
    if max_active != 5:
        raise ConfigError("MAX_ACTIVE_POLICY_MISMATCH")

    normalized = _normalized_config_values(
        config_version=config_version,
        classification=classification,
        mode=mode,
        account_equity=account_equity,
        leverage=leverage,
        quantity_step=quantity_step,
        price_tick=price_tick,
        adverse_cost_per_unit=adverse_cost,
        scalping_allocation=scalping,
        intraday_allocation=intraday,
        scalping_channel_id=scalping_channel_id,
        intraday_channel_id=intraday_channel_id,
        first_leg_risk=first_leg,
        max_active_setups=max_active,
    )
    canonical = json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return MvpConfig(
        config_version=config_version,
        classification=classification,
        mode=mode,
        account_equity=account_equity,
        leverage=leverage,
        quantity_step=quantity_step,
        price_tick=price_tick,
        adverse_cost_per_unit=adverse_cost,
        scalping_allocation=scalping,
        intraday_allocation=intraday,
        scalping_channel_id=scalping_channel_id,
        intraday_channel_id=intraday_channel_id,
        first_leg_risk=first_leg,
        max_active_setups=max_active,
        fingerprint=fingerprint,
    )


def load_config(path: str | Path) -> MvpConfig:
    try:
        config_path = Path(path)
        config_stat = config_path.stat()
        if config_path.is_symlink() or not stat.S_ISREG(config_stat.st_mode):
            raise ConfigError("CONFIG_READ_OR_PARSE_FAILED")
        with config_path.open("rb") as stream:
            raw = stream.read(MAX_CONFIG_BYTES + 1)
        if len(raw) > MAX_CONFIG_BYTES or any(token in raw for token in (b"[", b"]", b"{", b"}")):
            raise ConfigError("CONFIG_READ_OR_PARSE_FAILED")
        text = raw.decode("utf-8")
        data = tomllib.loads(text)
    except ConfigError:
        raise
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, RecursionError) as exc:
        raise ConfigError("CONFIG_READ_OR_PARSE_FAILED") from exc
    return config_from_mapping(data)
