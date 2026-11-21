# Tech steering — CrewKit

- Language: Python 3.11+, **standard library only**. No pip installs, ever.
- Core package lives in `core/crewkit/` and is imported by both apps via a
  tiny `sys.path` bootstrap in each app (no packaging step needed).
- State is a single JSON file per app (atomic write via temp file + rename).
- Config is JSON with environment-variable overrides prefixed `CREWKIT_`.
- Time handling: all timestamps UTC ISO-8601; intervals in seconds (float).
- Every module must be import-safe (no side effects at import time).
- Verification: `python3 tests/selftest.py` must pass with zero network.
- Style: type hints on public functions, docstrings that state behaviour,
  no prints in library code (apps own all output).
