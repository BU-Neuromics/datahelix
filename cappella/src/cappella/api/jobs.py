import uuid
from datetime import datetime
from typing import Any


class AsyncJobStore:
    """In-memory store for async job status tracking."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def create_job(self, job_type: str = "resolve", **kwargs: Any) -> str:
        """Create a new job and return its run_id."""
        run_id = str(uuid.uuid4())
        self._jobs[run_id] = {
            "run_id": run_id,
            "job_type": job_type,
            "status": "queued",
            "started_at": None,
            "finished_at": None,
            "samples_total": None,
            "samples_resolved": None,
            "error": None,
            "collection": None,
            "created_at": datetime.utcnow().isoformat() + "Z",
            **kwargs,
        }
        return run_id

    def update_job(self, run_id: str, **kwargs: Any) -> None:
        """Update fields on a job."""
        if run_id not in self._jobs:
            return
        self._jobs[run_id].update(kwargs)

    def get_job(self, run_id: str) -> dict[str, Any] | None:
        """Get job status dict or None if not found."""
        return self._jobs.get(run_id)

    def list_jobs(self, job_type: str | None = None) -> list[dict[str, Any]]:
        """List all jobs, optionally filtered by type."""
        jobs = list(self._jobs.values())
        if job_type is not None:
            jobs = [j for j in jobs if j.get("job_type") == job_type]
        return jobs


# Global default store (can be replaced in tests)
_default_store = AsyncJobStore()


def get_default_store() -> AsyncJobStore:
    return _default_store
