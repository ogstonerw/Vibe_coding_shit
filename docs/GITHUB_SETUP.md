# Настройка GitHub

## 1. Создание репозитория

Загрузите содержимое в приватный GitHub-репозиторий. Не добавляйте `.env`, Telegram `.session`, API keys или реальные channel/user IDs.

## 2. Branch protection / ruleset

Для `main` включите:

- pull request обязателен;
- минимум одно человеческое approval;
- code-owner review для `governance/`, execution/risk/exchange и workflows;
- status check `factory-check` обязателен;
- conversations должны быть resolved;
- force push и deletion запрещены;
- bypass только у владельца.

Скопируйте `.github/CODEOWNERS.example` в `.github/CODEOWNERS` и замените `@YOUR_GITHUB_LOGIN` на свой GitHub login.

## 3. Secrets

Production и paper credentials должны быть разными. Секреты хранятся в GitHub Environments или внешнем secret manager, а не в repository secrets без environment approval. Для environment `limited-live` и `live` назначьте required reviewer — владельца.

## 4. Labels

Создайте labels: `spec`, `architecture`, `implementation`, `risk-change`, `execution-change`, `security`, `paper-ready`, `owner-approval-required`, `blocked`.

## 5. PR-процесс

Одна задача из `tasks.md` — один небольшой PR. В описании обязательны AC IDs, команды проверки, reviewer handoffs и residual risks. Governance и live-related изменения никогда не объединяются с обычным refactoring.

