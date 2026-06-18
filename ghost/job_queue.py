"""
Job Queue — lightweight debounce + sequential processing for file events.

Architecture:
    Watchdog Handler -> TimerDebouncer -> JobQueue -> Worker

The watchdog handler calls queue.submit(file_path, callback).
The debouncer collapses rapid re-submits of the same path into one job.
The worker processes jobs in FIFO order on a dedicated thread.
"""

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from queue import Empty, Queue
from typing import Any, Callable, Optional


class JobState(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class Job:
    path: str
    callback: Callable[[str], Any]
    created_at: float = field(default_factory=time.time)
    state: JobState = JobState.PENDING
    error: Optional[str] = None


class TimerDebouncer:
    """Debounce layer: one timer per file path.

    Each new submit() for a path resets its timer. Only after *delay* seconds
    with no new events does the job proceed to the queue.
    """

    def __init__(self, on_ready: Callable[[str], None], delay: float = 2.0):
        self._on_ready = on_ready
        self._delay = delay
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def submit(self, path: str) -> None:
        with self._lock:
            existing = self._timers.get(path)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(self._delay, self._fire, args=[path])
            timer.daemon = True
            timer.start()
            self._timers[path] = timer

    def _fire(self, path: str) -> None:
        with self._lock:
            self._timers.pop(path, None)
        self._on_ready(path)

    def cancel(self, path: Optional[str] = None) -> None:
        with self._lock:
            if path:
                timer = self._timers.pop(path, None)
                if timer:
                    timer.cancel()
            else:
                for timer in self._timers.values():
                    timer.cancel()
                self._timers.clear()

    @property
    def pending_paths(self) -> list[str]:
        with self._lock:
            return list(self._timers.keys())


class JobQueue:
    """Ordered, single-worker job queue with per-file dedup.

    The watchdog handler should call ``queue.submit(path, callback)``.
    The worker picks up jobs in FIFO order and runs them on a single thread.
    """

    def __init__(
        self,
        debounce_seconds: float = 2.0,
        max_workers: int = 1,
    ):
        self._debounce_seconds = debounce_seconds
        self._max_workers = max_workers
        self._queue: Queue[Job] = Queue()
        self._workers: list[threading.Thread] = []
        self._running = False
        self._active: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.Lock()
        self._debouncer = TimerDebouncer(
            on_ready=self._enqueue,
            delay=debounce_seconds,
        )

    def submit(self, path: str, callback: Callable[[str], Any]) -> None:
        with self._lock:
            if path in self._active:
                self._active[path].callback = callback
                self._active.move_to_end(path)
            else:
                job = Job(path=path, callback=callback)
                self._active[path] = job

        self._debouncer.submit(path)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        for i in range(self._max_workers):
            t = threading.Thread(
                target=self._worker_loop,
                name=f"ghost-worker-{i}",
                daemon=True,
            )
            t.start()
            self._workers.append(t)

    def stop(self, timeout: float = 10.0) -> None:
        self._running = False
        self._debouncer.cancel()
        for t in self._workers:
            t.join(timeout=timeout)
        self._workers.clear()

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    @property
    def debouncing_count(self) -> int:
        return len(self._debouncer.pending_paths)

    def _enqueue(self, path: str) -> None:
        with self._lock:
            job = self._active.pop(path, None)
        if job is not None:
            self._queue.put(job)

    def _worker_loop(self) -> None:
        while self._running:
            try:
                job = self._queue.get(timeout=0.5)
            except Empty:
                continue

            job.state = JobState.RUNNING
            try:
                job.callback(job.path)
                job.state = JobState.COMPLETED
            except Exception as exc:
                job.state = JobState.FAILED
                job.error = f"{type(exc).__name__}: {exc}"
            finally:
                self._queue.task_done()
