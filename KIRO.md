# How CrewKit was built with Kiro

CrewKit was built **spec-first** with Kiro CLI 3.5.0 (`kiro-cli`), logged in
with the project's Kiro account. The [`.kiro/`](.kiro/) directory in this
repo is the real working configuration used during the build — not an
after-the-fact decoration.

## Steering (`.kiro/steering/`)

Three steering files governed every generation session:

- `product.md` — what CrewKit is, the two proof apps, and the product rules
  (lean core, offline `--demo` modes, notifications as the product's voice).
- `tech.md` — Python 3.11+ standard library only, atomic JSON state,
  `CREWKIT_*` env overrides, import-safety, the self-test contract.
- `structure.md` — the folder contract: apps talk to the core only through
  its public API, and each app folder stays self-contained.

## Spec-driven development (`.kiro/specs/crewkit-core/`)

The core was specified before it was written:

- `requirements.md` — R1–R5 (config, scheduler, state store, notifier,
  runner) plus R6, the self-verification contract.
- `design.md` — one module per responsibility and the failure policy
  (a raising job never kills the loop).
- `tasks.md` — the checklist the build sessions worked through.

## Custom agent (`.kiro/agents/crewkit-builder.json`)

Created with `kiro-cli agent create crewkit-builder` and given a prompt
that pins it to the steering files and specs, stdlib-only code, and a hard
rule: *finish by running `python3 tests/selftest.py` and fixing failures
until it passes.*

## Build sessions (Kiro CLI, non-interactive)

1. **Core session** — implemented `core/crewkit/` (config, clock, store,
   notify, runner) and `tests/selftest.py` from the spec: 32 tests, all
   passing; core landed at 433 LOC against the 700 LOC steering budget.
2. **Apps session** — built both apps strictly on the core's public API,
   added offline demo fixtures, and extended the self-test with subprocess
   smoke tests for both demo modes: 34/34 passing.

## Hook (`.kiro/hooks/run-selftest-on-save.json`)

A file-edited hook that re-runs the deterministic self-test whenever a
Python file under `core/` or `apps/` changes, so a broken skeleton is
caught at edit time rather than at demo time.

## Verification

Every claim above is reproducible from a clean checkout:

```bash
python3 tests/selftest.py                      # 34 tests, offline
python3 apps/telegram-task-bot/bot.py --demo   # prints a due-task reminder
python3 apps/price-watch/watch.py --demo       # prints a price-drop alert
```
