# Product steering — CrewKit

CrewKit is a lean "skeleton crew" automation template: one tiny, dependable
core that a solo builder can copy into a new project and immediately get
scheduling, configuration, state and notifications without a framework.

The template is proven by two distinct applications built on the same core:

1. `apps/telegram-task-bot` — a Telegram task-reminder bot.
2. `apps/price-watch` — a web price-watch notifier.

Product rules:

- The core stays small enough to read in one sitting (target < 700 LOC).
- Every app must run in a `--demo` mode with no accounts, tokens or network,
  so judges and new users can see real behaviour in under a minute.
- Notifications are the product's voice: clear, short, timestamped.
