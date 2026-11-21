# Design — crewkit-core

Modules (one responsibility each):

- `config.py` — `Config` dataclass + `load_config(path, defaults)`.
- `clock.py` — `now_iso()`, `parse_iso()`, `due_jobs(jobs, state, now)`.
- `store.py` — `StateStore(path)` with dict-like access + atomic `save()`.
- `notify.py` — `Notifier(sinks)`; sinks `ConsoleSink`, `FileSink`,
  `WebhookSink`; `notify(title, body)` formats `[ISO] title — body`.
- `runner.py` — `run_loop(...)` orchestrates scheduler + store + notifier.
- `__init__.py` — re-exports the public API named in the structure steering.

Data flow: app builds jobs (name → callable) → runner asks clock which are
due → executes → persists outcome in state → failures go to the notifier.

Failure policy: a raising job never kills the loop; its error is recorded
and notified, and its last-run still advances (no hot retry storms).
