"""Registry for in-flight hardware jobs, plus the QPU quota guard.

A deployed instance shares one IBM Quantum token with everyone who opens the
page, and the Open Plan budget is ~10 QPU-minutes per month. So the caps here
are deliberately process-wide rather than per-session: the resource being
protected is the token's monthly allowance, not any one player's fair share.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Protocol

from app.quantum.hardware import DownscaledProblem, JobUpdate

TTL_SECONDS = 6 * 3600
MAX_RECORDS = 200
HOUR = 3600.0
DAY = 24 * 3600.0


class QuotaExceeded(RuntimeError):
    """A rate limit would be crossed by submitting another job."""

    def __init__(self, message: str, retry_after: int) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class JobNotFound(KeyError):
    pass


@dataclass
class HardwareJobRecord:
    job_id: str
    game_id: str
    backend_name: str
    problem: DownscaledProblem
    shots: int
    depth: int
    two_qubit_gates: int
    ideal: list[float]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: str = "QUEUED"
    counts: dict[int, int] | None = None
    error: str | None = None
    qpu_seconds: float | None = None

    @property
    def finished(self) -> bool:
        return self.status in ("DONE", "CANCELLED", "ERROR")


class HardwareJobStore(Protocol):
    def reserve(self) -> float: ...
    def release(self, ticket: float) -> None: ...
    def add(self, record: HardwareJobRecord) -> None: ...
    def get(self, job_id: str) -> HardwareJobRecord: ...
    def apply(self, job_id: str, update: JobUpdate) -> HardwareJobRecord: ...


class InMemoryHardwareJobStore:
    def __init__(self, max_per_hour: int, max_per_day: int) -> None:
        self._max_per_hour = max_per_hour
        self._max_per_day = max_per_day
        self._submissions: list[float] = []
        self._records: dict[str, HardwareJobRecord] = {}
        self._lock = threading.Lock()

    # ---- quota ----

    def reserve(self) -> float:
        """Claim one submission slot. Returns a ticket for release() on failure."""
        now = time.time()
        with self._lock:
            self._submissions = [t for t in self._submissions if now - t < DAY]
            in_hour = [t for t in self._submissions if now - t < HOUR]
            if len(in_hour) >= self._max_per_hour:
                raise QuotaExceeded(
                    f"実機ジョブは1時間に{self._max_per_hour}件までです",
                    retry_after=int(HOUR - (now - min(in_hour))) + 1,
                )
            if len(self._submissions) >= self._max_per_day:
                raise QuotaExceeded(
                    f"実機ジョブは1日に{self._max_per_day}件までです",
                    retry_after=int(DAY - (now - min(self._submissions))) + 1,
                )
            self._submissions.append(now)
            return now

    def release(self, ticket: float) -> None:
        """Give a reserved slot back, for a submission that never reached the QPU."""
        with self._lock:
            try:
                self._submissions.remove(ticket)
            except ValueError:
                pass

    def quota_snapshot(self) -> tuple[int, int]:
        """(submissions in the last hour, in the last day)."""
        now = time.time()
        with self._lock:
            return (
                sum(1 for t in self._submissions if now - t < HOUR),
                sum(1 for t in self._submissions if now - t < DAY),
            )

    # ---- records ----

    def add(self, record: HardwareJobRecord) -> None:
        with self._lock:
            self._evict()
            self._records[record.job_id] = record

    def get(self, job_id: str) -> HardwareJobRecord:
        with self._lock:
            record = self._records.get(job_id)
            if record is None or time.time() - record.created_at > TTL_SECONDS:
                self._records.pop(job_id, None)
                raise JobNotFound(job_id)
            return record

    def apply(self, job_id: str, update: JobUpdate) -> HardwareJobRecord:
        record = self.get(job_id)
        with self._lock:
            record.status = update.status
            record.updated_at = time.time()
            if update.counts is not None:
                record.counts = update.counts
            if update.error is not None:
                record.error = update.error
            if update.qpu_seconds is not None:
                record.qpu_seconds = update.qpu_seconds
            return record

    def _evict(self) -> None:
        # Caller holds self._lock.
        now = time.time()
        for job_id in [
            k for k, r in self._records.items() if now - r.created_at > TTL_SECONDS
        ]:
            self._records.pop(job_id, None)
        if len(self._records) >= MAX_RECORDS:
            oldest = sorted(self._records.items(), key=lambda kv: kv[1].created_at)
            for job_id, _ in oldest[: len(self._records) - MAX_RECORDS + 1]:
                self._records.pop(job_id, None)
