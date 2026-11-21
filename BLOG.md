# Building CrewKit: a skeleton that grew two apps

*This post is written as part of the [Kiroween 2026](https://kiroween.devpost.com) hackathon — it documents how I built my Skeleton Crew entry, [CrewKit](https://devpost.com/software/crewkit), with Kiro.*

## The itch

Every automation project I start begins the same way: a scheduler, config loading, state that survives a crash, and a way to notify a human when something happens. I have written those four things from scratch more times than I can count, and every framework that offers them brings thousands of lines and a dependency tree along for the ride.

So for the Skeleton Crew category — *a lean skeleton template, proven by two distinct applications* — I built the bones exactly once, in the open, with an AI agent doing most of the typing under unusually strict house rules.

The result: **CrewKit**, a 433-line core in pure stdlib Python (zero dependencies), with two working apps on top of it:

- a **Telegram task-reminder bot** (`/add`, `/list`, `/done`, due-task nudges), and
- a **price-watch notifier** that extracts prices from JSON-LD and alerts when a target is hit.

Same bones. Two completely different creatures.

## Spec first, code second

The part of Kiro that changed how I work is not autocomplete — it is the `.kiro` directory as a *contract*:

- **Steering files** (`product.md`, `tech.md`, `structure.md`) fixed the rules before any code existed: stdlib only, a 700-line budget for the core, apps may only touch the core's public API, every app must run offline in a `--demo` mode.
- **A spec** (`requirements.md` R1–R6, `design.md`, `tasks.md`) described the core module by module: config, clock, store, notify, runner — and the failure policy ("a raising job never kills the loop").
- **A custom agent** (`crewkit-builder`, created with `kiro-cli agent create`) whose prompt pinned it to the steering + spec and ended with a hard rule: *you are not finished until `python3 tests/selftest.py` passes.*
- **A hook** that re-runs the self-test whenever a Python file is edited, so a broken skeleton gets caught at edit time, not demo time.

Two Kiro CLI sessions later — one for the core, one for both apps — I had 32 passing tests, then 34, and I had barely written any of the implementation myself. My job had moved up a level: writing requirements sharp enough that "done" is checkable, then verifying the evidence instead of the prose.

## My favorite thing about Kiro

The finish line moved. In my old workflow, an AI session ended when the output *looked* right. With specs + steering + a custom agent, the session ends when a deterministic test suite says it is right — the agent iterates against the tests, not against my patience. The core landed at 433 lines against its 700-line budget not because I counted, but because the steering file did.

That is the change I am taking to every future project: **give the agent a contract and a test, not a vibe.**

## Proof, not promises

Everything in CrewKit is verifiable from a clean checkout, offline:

```bash
python3 tests/selftest.py                    # 34 tests, ~0.25 s
python3 apps/telegram-task-bot/bot.py --demo # prints a due-task reminder
python3 apps/price-watch/watch.py --demo     # prints a price-drop alert
```

- Repo (MIT, with the full `.kiro/` directory): https://github.com/kontenlaris-studio/crewkit
- Live demo site: https://kontenlaris-studio.github.io/crewkit/
- Demo video (2:42): https://www.youtube.com/watch?v=6Fuo2gpA0ok
- Devpost project: https://devpost.com/software/crewkit

## What I would do next

More notifier sinks (ntfy, Slack), a third proof app (an RSS digest — the classic skeleton stress test), and a `crewkit new <app>` scaffolder generated from the same spec workflow. The skeleton held up under two apps; a third will tell me if it is a template or just a coincidence.

*Built with Kiro CLI (specs, steering, hooks, custom agents) for Kiroween 2026, Skeleton Crew category.*
