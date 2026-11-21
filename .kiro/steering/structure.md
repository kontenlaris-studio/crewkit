# Structure steering — CrewKit

```
core/crewkit/            the reusable skeleton (config, clock, store, notify, runner)
apps/telegram-task-bot/  app 1 — its own folder, README, entry point, demo data
apps/price-watch/        app 2 — its own folder, README, entry point, demo data
tests/                   deterministic self-tests for core + both apps
docs/                    GitHub Pages demo site
.kiro/                   steering, specs, hooks, agents (never gitignored)
```

Rules:

- Apps may only talk to the core through its public API
  (`Config`, `StateStore`, `Notifier`, `Scheduler`, `run_loop`).
- Each app folder must be self-contained: copying `core/` + one app folder
  into a fresh directory must yield a runnable app.
- Demo fixtures live inside each app folder (`demo.json`), never in core.
