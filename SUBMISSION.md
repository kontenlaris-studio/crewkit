# Devpost submission — CrewKit (Kiroween 2026, Skeleton Crew)

**Project name:** CrewKit

**Tagline:** One tiny core. A crew of apps. A dependency-free automation skeleton, proven by two apps.

**Category:** Skeleton Crew
**Bonuses to consider:** Best Demo (automatic)

## Inspiration
Every automation project I start re-builds the same bones: a scheduler, config loading, state that survives a crash, and a way to notify a human. Frameworks solve this with thousands of lines and a dependency tree. For Kiroween's Skeleton Crew category I wanted the opposite: the smallest honest skeleton a solo builder can read in one sitting — and proof that it is a real template, not a toy, by shipping two genuinely different applications on top of it.

## What it does
CrewKit is a lean automation template in pure stdlib Python (no pip installs):
- `core/crewkit/` (~433 LOC): `config.py` (JSON + env overrides), `clock.py` (UTC time + a pure due-job scheduler), `store.py` (atomic JSON state via temp-file + rename), `notify.py` (console/file/webhook sinks), `runner.py` (runs due jobs, records outcomes, alerts on failure — a raising job never kills the loop).
- App 1 — `apps/telegram-task-bot/`: a Telegram task-reminder bot (`/add`, `/list`, `/done`) whose scheduler job nudges you when tasks fall due.
- App 2 — `apps/price-watch/`: watches product pages, extracts prices from JSON-LD (regex fallback), and alerts the moment a price hits your target.
Both apps run in an offline `--demo` mode — no accounts, tokens or network — and each app folder is self-contained: copy `core/` + one app folder anywhere and it runs.

## How I built it
Spec-first with Kiro CLI. The repo's `.kiro/` directory is the actual build configuration: steering files (product/tech/structure), a written spec (requirements R1–R6, design, tasks), a custom `crewkit-builder` agent created with `kiro-cli agent create`, and a hook that re-runs the deterministic self-test on every Python edit. Two Kiro sessions built the core and then both apps, each under a hard rule: finish only when `python3 tests/selftest.py` passes. Full story in KIRO.md in the repo.

## Challenges I ran into
Keeping the core honest: the scheduler had to stay a pure function of (now, state) so demos and tests could use a fake clock; state writes had to be atomic without any library help; and the two apps had to stay strictly on the core's public API — no reaching into internals — or the "template" claim would be hollow.

## Accomplishments that I'm proud of
34/34 deterministic tests pass offline in ~0.25 s, including subprocess smoke tests that run both apps' demo modes end to end. The core landed at 433 lines against a 700-line steering budget. Zero dependencies: clone, run, ship.

## What I learned
A small spec plus a strict steering budget beats a big prompt. Letting Kiro generate against written requirements — and forcing every session to end at a green self-test — produced code that needed almost no hand-fixing.

## What's next for CrewKit
More sinks (ntfy, Slack), a third proof app (RSS digest), and a `crewkit new <app>` scaffolding command generated from the same spec workflow.

**Built with:** Kiro (CLI, specs, steering, hooks, custom agents), Python 3 (standard library only), GitHub Pages

**Links:**
- Repo: https://github.com/kontenlaris-studio/crewkit
- Live demo site: https://kontenlaris-studio.github.io/crewkit/
- Video: https://www.youtube.com/watch?v=6Fuo2gpA0ok (PUBLIC, 2:42)
- License: MIT (in repo)
