"""
Custom RQ Worker (non-forking version).

This module overrides the default RQ worker behavior for controlled
job execution inside the same process/thread — useful for:
- Testing environments (no fork(), easier debugging)
- Dockerized setups where forking causes permission or resource issues
- Environments where multiprocessing is restricted (e.g., some shared hosts)

Key points:
- `BaseDeathPenalty`: dummy context manager replacing RQ’s timeout killer.
- `SimpleWorker`: subclass of RQ’s SimpleWorker that disables forking.

Usage:
--------
This worker is typically referenced by Django RQ configuration
(e.g., `RQ_QUEUES`) or used manually in testing.
"""

from rq import SimpleWorker


class BaseDeathPenalty:
    """
    No-op (dummy) death penalty context manager.

    Normally, RQ uses a `DeathPenalty` to kill jobs exceeding a timeout.
    Here, this class disables that behavior — useful for debugging or tests
    where we don’t want jobs to be terminated automatically.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self, *args, **kwargs):
        """Enter context (does nothing)."""
        pass

    def __exit__(self, *args, **kwargs):
        """Exit context (does nothing)."""
        pass


class SimpleWorker(SimpleWorker):
    """
    Non-forking RQ worker subclass.

    Normally, RQ forks a subprocess for each job.
    This worker executes jobs directly in the same thread/process
    for simplicity and better compatibility inside certain containers.
    """

    death_penalty_class = BaseDeathPenalty

    def main_work_horse(self, *args, **kwargs):
        """
        Override the method responsible for creating a forked process.

        Since this custom worker does not fork, this method raises an error
        to prevent unexpected calls.
        """
        raise NotImplementedError("Test worker does not implement this method")

    def execute_job(self, *args, **kwargs):
        """
        Execute job inline (in the same process/thread).

        This overrides RQ’s default execute_job() to avoid fork().
        Useful for testing or constrained environments.
        """
        return self.perform_job(*args, **kwargs)
