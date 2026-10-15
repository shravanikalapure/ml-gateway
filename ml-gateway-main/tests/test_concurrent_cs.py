"""
Concurrency tests for Ricart–Agrawala Mutual Exclusion Algorithm.
Verifies no overlapping critical section execution and deadlock-free progress.
"""

import time
import threading
import pytest
from gateway.mutual_exclusion import RicartAgrawalaManager


def test_concurrent_critical_section_access():
    ra = RicartAgrawalaManager()

    active_in_cs = 0
    max_active_in_cs = 0
    lock_stats = threading.Lock()
    errors = []

    def process_worker(pid: str):
        nonlocal active_in_cs, max_active_in_cs
        try:
            # Request critical section
            res = ra.request_cs(pid)

            # Wait if deferred until we hold CS
            start_wait = time.time()
            while True:
                status = ra.get_status()
                if status["current_cs_holder"] == pid:
                    break
                if time.time() - start_wait > 5.0:
                    raise TimeoutError(f"Process {pid} timed out waiting for Critical Section entry.")
                time.sleep(0.01)

            # Critical section entry
            with lock_stats:
                active_in_cs += 1
                if active_in_cs > max_active_in_cs:
                    max_active_in_cs = active_in_cs
                # Assert invariant: only 1 process can be in CS
                if active_in_cs > 1:
                    errors.append(f"Mutual exclusion violated! {active_in_cs} processes in CS.")

            # Simulate critical section work
            time.sleep(0.02)

            # Critical section exit
            with lock_stats:
                active_in_cs -= 1

            # Release CS
            ra.release_cs(pid)

        except Exception as e:
            errors.append(str(e))

    # Run P1, P2, P3 concurrently
    threads = [
        threading.Thread(target=process_worker, args=("P1",)),
        threading.Thread(target=process_worker, args=("P2",)),
        threading.Thread(target=process_worker, args=("P3",)),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert len(errors) == 0, f"Errors encountered during concurrent execution: {errors}"
    assert max_active_in_cs == 1, f"Expected exactly 1 max process in CS, got {max_active_in_cs}"
    assert active_in_cs == 0

    status = ra.get_status()
    assert status["cs_occupied"] is False
    assert status["current_cs_holder"] is None
    for pid in ["P1", "P2", "P3"]:
        assert status["processes"][pid]["state"] == "RELEASED"
        assert status["processes"][pid]["cs_entries"] == 1
