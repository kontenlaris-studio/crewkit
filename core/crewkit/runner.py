"""Runner module: orchestrates scheduling, execution, state and notifications."""

from typing import Any, Callable, Dict, Optional
from .clock import now_iso, due_jobs
from .store import StateStore
from .notify import Notifier


def run_loop(
    jobs: Dict[str, Callable],
    store: StateStore,
    notifier: Notifier,
    now_fn: Callable[[], str] = now_iso,
    ticks: int = 1
) -> Dict[str, Any]:
    """
    Execute due jobs and record their outcomes.
    
    Args:
        jobs: dict mapping job_name -> callable
        store: StateStore for persisting job state
        notifier: Notifier for sending failure alerts
        now_fn: function that returns current time as ISO-8601 (default: now_iso)
        ticks: number of iterations to run (for testing/demo)
    
    Returns:
        Summary dict with keys:
            - executed: list of job names executed
            - failed: list of job names that raised exceptions
            - summary: human-readable summary
    """
    executed = []
    failed = []
    
    for _ in range(ticks):
        now = now_fn()
        
        # Determine which jobs are due
        job_configs = {}
        for job_name in jobs.keys():
            job_configs[job_name] = {'interval_seconds': 0}  # 0 means always due if never run
        
        # Use store's state to make scheduling decision
        state = store.to_dict()
        due_list = due_jobs(job_configs, state, now)
        
        # Execute due jobs
        for job_name in due_list:
            if job_name not in jobs:
                continue
            
            job_fn = jobs[job_name]
            
            # Initialize job state if needed
            if job_name not in state:
                state[job_name] = {}
            
            try:
                # Execute job
                result = job_fn()
                executed.append(job_name)
                
                # Record success
                state[job_name]['last_run'] = now
                state[job_name]['last_result'] = 'success'
                state[job_name]['last_error'] = None
                
            except Exception as e:
                failed.append(job_name)
                error_msg = str(e)
                
                # Record failure
                state[job_name]['last_run'] = now
                state[job_name]['last_result'] = 'failure'
                state[job_name]['last_error'] = error_msg
                
                # Notify about failure
                notifier.notify(
                    title=f"Job failed: {job_name}",
                    body=error_msg,
                    timestamp=now
                )
        
        # Persist state after each tick
        for key, value in state.items():
            store[key] = value
        store.save()
    
    return {
        'executed': executed,
        'failed': failed,
        'summary': f"Executed {len(executed)} job(s), {len(failed)} failed"
    }
