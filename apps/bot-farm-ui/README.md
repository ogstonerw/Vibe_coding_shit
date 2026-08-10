# ИИагент — Ферма ботов

Первый standalone-фронтенд TradeBot Agent Factory. Это React/TypeScript/Vite-приложение с расширяемой пиксельной картой market-зданий. Каждый NPC представляет конкретного бота/агента: Crypto-курятник содержит три crypto-NPC, MOEX-амбар резервирует три места, а Risk и Review живут в собственных зданиях. Паспорт единственного реализованного торгового бота TB-001 и остальные витрины остаются read-only.

Интерфейс работает только с типизированными mock-данными. Он не импортирует Python-код проекта, не читает SQLite, не вызывает Telegram/Bitget API, не запускает subprocess и не создаёт ордера. Paper и Live остаются заблокированы.

## Запуск

Требуется Node.js 20.19+.

```powershell
cd apps/bot-farm-ui
npm install
npm run dev
```

Vite выведет локальный URL, обычно `http://localhost:5173`.

## Проверки

```powershell
npm run typecheck
npm run test
npm run build
```

## Маршруты

- `/` — карта зданий и шести NPC-ботов; Owner перемещается между зданиями стрелками или экранным D-pad, а торговая реализация есть только у TB-001;
- `/bots/:botId` — паспорт, стадии, gates и review evidence;
- `/test-lab` — локальные mock-анимации наборов тестов;
- `/risk` — read-only лестница защитных состояний; без telemetry активное состояние `NOT_EVALUATED`;
- `/releases` — Slice 02 и независимые Owner Merge/Pilot/Live gates;
- `/reviews` — пять независимых review-ролей.
- `/events`, `/notifications`, `/builds` — локальные read-only utility-витрины;
- `/docs` — встроенный путеводитель по UI и safety boundaries.

## Архитектурный seam

UI получает `FarmSnapshot` через `BotFarmRepository` и React context. Текущая композиция связывает интерфейс с `MockBotFarmRepository`. Будущий API-адаптер можно подставить в provider, не меняя страницы и компоненты:

```text
pages/components → FarmDataProvider → BotFarmRepository
                                      └─ MockBotFarmRepository (сейчас)
```

Mock-данные находятся в `src/data/mock/mockData.ts`; доменная модель — в `src/domain/botFarm.ts`.

Карта не использует readiness-проценты. Движение Owner и mock-запуски Test Lab
не делают сетевых запросов и не меняют gate, runtime или торговое состояние.
