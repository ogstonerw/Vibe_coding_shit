# UI/UX architecture

Статус: **OWNER DIRECTION ACCEPTED — DECISIONS 1–7 RECORDED**.

Этот каталог фиксирует аудит и черновую архитектуру интерфейса «ИИагент —
Ферма ботов». Документы не дают разрешения на Paper/Live и не меняют
торговую логику.

- [PRODUCT_UX_ARCHITECTURE.md](PRODUCT_UX_ARCHITECTURE.md) — аудит,
  product map, draft IA, lifecycle, каталог экранов и порядок проектирования.
- [DESIGN_AND_OPERATIONS_REVIEW.md](DESIGN_AND_OPERATIONS_REVIEW.md) —
  независимые позиции Designer и Pro Trader, спорные решения и вопросы Owner.
- [OWNER_DECISIONS.md](OWNER_DECISIONS.md) — принятые решения Owner, простое
  объяснение составного состояния и неизменяемые safety boundaries.
- [MENU_ARCHITECTURE.md](MENU_ARCHITECTURE.md) — global/domain/context
  navigation, menus, dock, command palette и module registry.
- [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) — pixel/cozy foundations и строгие
  professional data/evidence components.
- [MOTION_SYSTEM.md](MOTION_SYSTEM.md) — interaction, NPC/ambient и safety-aware
  motion с reduced-motion/performance limits.
- [SCREEN_CATALOG.md](SCREEN_CATALOG.md) — подробные contracts для всех 37
  current/planned screens.

Текущий implementation slice реализует расширяемые здания, NPC-ботов и
навигацию Owner. Foundation UI-022-001 описывает следующий Operations/design
slice, но не реализует новый shell. Backend integration остаётся отдельным
будущим этапом.
