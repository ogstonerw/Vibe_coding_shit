# Token-efficient review protocol

Цель: продолжать разработку без повторного чтения завершённой истории и без
пропуска обязательных gates.

## 1. Минимальный startup

1. Прочитать только:
   - `AGENTS.md`;
   - `HANDOFF_NEW_CHAT_RU.md`;
   - `docs/FROZEN_CORE_V11.sha256`;
   - `docs/FROZEN_PM_DEC_007_HYBRID_V1.sha256`.
2. Проверить оба manifest:

   ```bash
   sha256sum docs/FROZEN_CORE_V11.sha256
   sha256sum -c docs/FROZEN_CORE_V11.sha256
   sha256sum docs/FROZEN_PM_DEC_007_HYBRID_V1.sha256
   sha256sum -c docs/FROZEN_PM_DEC_007_HYBRID_V1.sha256
   ```

   Ожидаемые SHA:

   - core:
     `46f20183230d84f6fdaba9ccc63e8e504afcd2be77c4447c66a14f5a9be5390f`;
   - PM-DEC-007 addendum:
     `f6b8e859365bc00335b7a5b5b1a577c7784ebc75661f4f573839c98abcafcd53`.
3. Если manifests и все `10 + 9` entries совпадают, не читать старый полный
   chat, прежние handoff-архивы или прошлые reviewer narratives.
4. ZIP-файлы проверять по hash и штатным snapshot tests; не распаковывать их
   без mismatch.
5. При mismatch остановиться, назвать изменённые raw paths и исследовать только
   их acceptance impact.

## 2. Исполнение и review

1. Один persistent writer на весь correction loop; parallel writers запрещены.
2. После реализации сначала test engineer и deterministic gates.
3. Code/security/risk reviewers получают только domain acceptance IDs, frozen
   hashes, raw paths и точные команды воспроизведения. Авторское резюме не
   является evidence.
4. Writer получает только unresolved reproducible findings с severity,
   location, fixture/command и ожидаемым fail-closed результатом.
5. После correction повторять correction-scoped checks, затем полный gate set.
6. На final raw artifacts проводить fresh institutional, quant-methodology и
   market-microstructure reviews.
7. Release verifier запускается последним и не может отменить failed gate.

## 3. Коммуникация

- Давать status только на границах стадий: freeze, implementation, focused/full
  gates, review verdicts, release verdict.
- Формат: `VERDICT`, `SCOPE`, `FINDINGS`, `RAW EVIDENCE`, `GATES`, `NEXT`.
- При owner decision, конфликте источников истины или расширении authority
  немедленно остановиться.
- Live trading, real orders, production credentials и real-capital authority
  остаются `BLOCKED / DENY`; MOEX — `FUTURE / BLOCKED`.

## 4. Обязательные финальные gates

```bash
python3 scripts/check_pm_dec007_hybrid.py
python3 -m unittest tests.test_pm_dec007_hybrid -v
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
python3 -m py_compile \
  scripts/self_check.py \
  scripts/check_pm_dec007_hybrid.py \
  tests/test_portfolio_mandate.py \
  tests/test_pm_dec007_hybrid.py
sha256sum -c docs/FROZEN_CORE_V11.sha256
sha256sum -c docs/FROZEN_PM_DEC_007_HYBRID_V1.sha256
```

Завершённые scopes не переоткрывать без manifest mismatch или изменения их
semantics:

- `PM-REQ-082…093 / PM-AC-053…058`;
- `PM-REQ-094…096 / PM-AC-059…061`.
