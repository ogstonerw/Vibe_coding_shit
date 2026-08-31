# System Map

```text
GitHub schedule/manual trigger
        |
        v
factory.daily_run --dry-run
        |
        +--> registry validation
        +--> frozen/governance verification
        +--> repository and budget preflight
        +--> deterministic READY selection
        |
        v
execution plan + Owner Report
```

There is no connection to Codex, Telegram, Bitget, orders, positions, Paper, Live, commits, pushes, pull requests, or merge.
