# Requirements — crewkit-core

## R1 Config
Load JSON config from a path; missing file yields defaults; keys may be
overridden by `CREWKIT_<KEY>` environment variables (upper-case key name).

## R2 Scheduler
Given named jobs with `interval_seconds` and last-run timestamps, decide
which jobs are due. Pure function of (now, state) — no sleeping inside.

## R3 State store
JSON file store with `get`/`set`/`save`; writes are atomic
(temp file + `os.replace`); a corrupt file loads as empty state.

## R4 Notifier
A `Notifier` that fans a message out to sinks: console, append-only log
file, and webhook (stdlib `urllib`, best-effort, 5 s timeout, never raises).

## R5 Runner
`run_loop(config, jobs, store, notifier, ticks)` executes due jobs,
records last-run + last result in state, notifies on job failure,
and returns a summary dict. `ticks` bounds iterations for demo/test use.

## R6 Self-verification
`tests/selftest.py` covers R1–R5 deterministically with temp dirs and a
fake clock; it must pass offline in under 10 seconds.
