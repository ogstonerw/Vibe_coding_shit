# ИИагент — Ферма ботов

Первый standalone-фронтенд TradeBot Agent Factory. Это React/TypeScript/Vite-приложение с пиксельной картой шести агентов/служб, паспортом единственного реализованного торгового бота TB-001 и read-only витринами тестов, риска, релизов и ревью.

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

- `/` — единая карта шести prototype-сущностей; торговая реализация есть только у TB-001;
- `/bots/:botId` — паспорт, стадии, gates и review evidence;
- `/test-lab` — локальные mock-анимации наборов тестов;
- `/risk` — read-only лестница защитных состояний;
- `/releases` — Slice 02 и его owner/paper/live gates;
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
