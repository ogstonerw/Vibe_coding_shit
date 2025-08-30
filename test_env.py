import os, re
from dotenv import load_dotenv

REQUIRED = [
    "API_ID","API_HASH","TG_SESSION",
    # один из источников для каждого канала: либо LINK, либо NAME
    "TG_SOURCE_SCALPING_LINK","TG_SOURCE_SCALPING_NAME",
    "TG_SOURCE_INTRADAY_LINK","TG_SOURCE_INTRADAY_NAME",
    "TGBOT_TOKEN",
    # либо TG_OWNER_ID, либо TG_OWNER_IDS
    # "TG_OWNER_ID",
    "BITGET_API_KEY","BITGET_API_SECRET","BITGET_PASSPHRASE",
    "DRY_RUN","EQUITY_USDT","SPLIT_SCALPING_PCT","SPLIT_INTRADAY_PCT",
    "RISK_TOTAL_CAP_PCT","RISK_LEG_PCT","LEVERAGE_MIN","LEVERAGE_MAX",
    "BREAKEVEN_AFTER_TP","TIME_STOP_MIN"
]

def main():
    load_dotenv()
    missing = []
    issues = []

    # базовая проверка наличия
    for k in REQUIRED:
        if os.getenv(k) is None:
            missing.append(k)

    # спец-проверки
    key = os.getenv("BITGET_API_KEY","")
    if " " in key:
        issues.append("BITGET_API_KEY содержит пробелы — это сломает аутентификацию.")

    # проверка владельцев
    owner = os.getenv("TG_OWNER_ID")
    owners = os.getenv("TG_OWNER_IDS")
    if not owner and not owners:
        issues.append("Не задан TG_OWNER_ID (или TG_OWNER_IDS). Бот управления будет открыт всем — опасно.")
    if owners:
        for part in owners.split(","):
            if not part.strip().isdigit():
                issues.append(f"TG_OWNER_IDS содержит нечисловое значение: {part!r}")

    # проверка источников каналов: хотя бы одно поле на канал
    if not (os.getenv("TG_SOURCE_SCALPING_LINK") or os.getenv("TG_SOURCE_SCALPING_NAME")):
        issues.append("Для SCALPING задай либо TG_SOURCE_SCALPING_LINK, либо TG_SOURCE_SCALPING_NAME.")
    if not (os.getenv("TG_SOURCE_INTRADAY_LINK") or os.getenv("TG_SOURCE_INTRADAY_NAME")):
        issues.append("Для INTRADAY задай либо TG_SOURCE_INTRADAY_LINK, либо TG_SOURCE_INTRADAY_NAME.")

    # вывод
    if missing:
        print("❌ Отсутствуют переменные:", ", ".join(missing))
    else:
        print("✅ Все обязательные ключи присутствуют (базовая проверка).")
    if issues:
        print("⚠️ Найдены проблемы:")
        for i in issues:
            print(" -", i)
    else:
        print("✅ Явных проблем не найдено.")

if __name__ == "__main__":
    main()
