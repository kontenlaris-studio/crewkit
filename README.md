# CrewKit — a skeleton-crew automation template

**One tiny core. A crew of apps.** CrewKit is a lean, dependency-free
automation skeleton built with [Kiro](https://kiro.dev) for the
**Kiroween 2026 — Skeleton Crew** category: a small core template
(scheduler, config, state, notifications) proven by **two distinct
applications** living in their own folders.

No frameworks. No pip installs. Python 3.11+ standard library only —
copy the folder, run it, ship it.

## The skeleton (`core/crewkit/`, ~430 LOC)

| Module | Job |
| --- | --- |
| `config.py` | JSON config + `CREWKIT_*` env overrides |
| `clock.py` | UTC ISO-8601 time + a pure due-job scheduler |
| `store.py` | Atomic JSON state (temp file + rename, crash-safe) |
| `notify.py` | Notifier with console / file / webhook sinks |
| `runner.py` | Loop that runs due jobs, records outcomes, alerts on failure |

## The crew (two apps, one core)

### 1. Telegram Task Bot — `apps/telegram-task-bot/`
Task reminders on the skeleton. Add tasks from Telegram
(`/add title | minutes`, `/list`, `/done id`); the scheduler job nudges you
when they fall due.

```bash
python3 apps/telegram-task-bot/bot.py --demo   # offline demo, no token needed
BOT_TOKEN=... python3 apps/telegram-task-bot/bot.py   # live mode
```

### 2. Price Watch — `apps/price-watch/`
Watches product pages and notifies you the moment a price drops to your
target. Prices are extracted from JSON-LD first, with a regex fallback.

```bash
python3 apps/price-watch/watch.py --demo       # offline demo with sample pages
python3 apps/price-watch/watch.py              # live mode with your watchlist
```

## Verify everything

```bash
python3 tests/selftest.py
```

Deterministic, offline, a few seconds: unit tests for the core (R1–R5)
plus smoke tests that run both apps' demo modes end to end.

## Use the skeleton for your own app

1. Copy `core/` next to a new `apps/<your-app>/` folder.
2. Bootstrap `sys.path` the way the two sample apps do (3 lines).
3. Build jobs as plain callables, hand them to `run_loop`, done.

## How it was built with Kiro

See [KIRO.md](KIRO.md) — spec-driven development with the steering files,
spec and hook in [`.kiro/`](.kiro/), plus a custom `crewkit-builder` agent.

## License

MIT — see [LICENSE](LICENSE).
