import time

from ghost.job_queue import JobQueue, JobState


class TestJobQueue:
    def test_submit_and_process(self):
        results = []
        queue = JobQueue(debounce_seconds=0.05, max_workers=1)
        queue.start()

        def callback(path):
            results.append(path)

        queue.submit("/test/file.py", callback)
        time.sleep(0.3)
        queue.stop()

        assert "/test/file.py" in results

    def test_debounce_collapses_rapid_submits(self):
        results = []
        queue = JobQueue(debounce_seconds=0.2, max_workers=1)
        queue.start()

        def callback(path):
            results.append(path)

        queue.submit("/test/file.py", callback)
        time.sleep(0.05)
        queue.submit("/test/file.py", callback)
        time.sleep(0.05)
        queue.submit("/test/file.py", callback)
        time.sleep(0.5)
        queue.stop()

        assert len(results) == 1

    def test_multiple_paths_process_separately(self):
        results = []
        queue = JobQueue(debounce_seconds=0.05, max_workers=1)
        queue.start()

        def callback(path):
            results.append(path)

        queue.submit("/test/a.py", callback)
        queue.submit("/test/b.py", callback)
        time.sleep(0.3)
        queue.stop()

        assert len(results) == 2
        assert "/test/a.py" in results
        assert "/test/b.py" in results

    def test_pending_count(self):
        queue = JobQueue(debounce_seconds=5.0, max_workers=1)
        queue.start()

        def callback(path):
            pass

        assert queue.pending_count == 0
        queue.submit("/test/file.py", callback)
        time.sleep(0.1)
        queue.stop()

    def test_stop_cleans_up(self):
        queue = JobQueue(debounce_seconds=0.05, max_workers=1)
        queue.start()

        def callback(path):
            pass

        queue.submit("/test/file.py", callback)
        queue.stop(timeout=2.0)

        assert not queue._running


class TestJobState:
    def test_enum_values(self):
        assert JobState.PENDING.name == "PENDING"
        assert JobState.RUNNING.name == "RUNNING"
        assert JobState.COMPLETED.name == "COMPLETED"
        assert JobState.FAILED.name == "FAILED"
