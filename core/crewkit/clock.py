"""Clock module: time handling in UTC ISO-8601 format."""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


def now_iso() -> str:
    """Return current UTC time as ISO-8601 string (Z suffix)."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_iso(iso_str: str) -> datetime:
    """
    Parse ISO-8601 string to datetime object (UTC).
    Handles both Z and +00:00 suffixes.
    """
    # Replace Z with +00:00 for compatibility
    if iso_str.endswith('Z'):
        iso_str = iso_str[:-1] + '+00:00'
    
    return datetime.fromisoformat(iso_str)


def due_jobs(
    jobs: Dict[str, Dict[str, Any]],
    state: Dict[str, Any],
    now: str
) -> List[str]:
    """
    Determine which jobs are due to run.
    
    Args:
        jobs: dict of job_name -> {interval_seconds, ...}
        state: dict of job_name -> {last_run: ISO-8601, ...}
        now: current time as ISO-8601 string
    
    Returns:
        List of job names that are due.
    """
    now_dt = parse_iso(now)
    due = []
    
    for job_name, job_config in jobs.items():
        interval = job_config.get('interval_seconds')
        if interval is None:
            continue
        
        # Get last run time from state, or use epoch if never run
        job_state = state.get(job_name, {})
        last_run_str = job_state.get('last_run')
        
        if last_run_str is None:
            # Never run before, so it's due
            due.append(job_name)
        else:
            try:
                last_run_dt = parse_iso(last_run_str)
                elapsed = (now_dt - last_run_dt).total_seconds()
                if elapsed >= interval:
                    due.append(job_name)
            except (ValueError, TypeError):
                # Corrupt last_run timestamp; treat as due
                due.append(job_name)
    
    return due
