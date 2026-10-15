"""
Unit and integration tests for Serverless Architecture and FaaS Runtime Simulation (Unit IV)
"""

import time
import pytest
from gateway.serverless import ServerlessRuntime


def test_first_invocation_is_cold_start():
    runtime = ServerlessRuntime()
    res = runtime.invoke([1.0, 2.0, 3.0, 4.0], model_name="demo-model")

    assert res["is_cold_start"] is True
    assert res["initialization_time_ms"] > 0
    assert res["execution_time_ms"] > 0
    assert res["runtime_state"] == "WARM"
    assert res["container_id"] is not None
    assert res["output_tensor"] == [1.5, 3.0, 4.5, 6.0]
    assert res["simulated_memory"]["total_simulated_mb"] > 128.0

    metrics = runtime.get_metrics()
    assert metrics["total_invocations"] == 1
    assert metrics["cold_starts"] == 1
    assert metrics["warm_starts"] == 0


def test_subsequent_invocations_reuse_warm_container():
    runtime = ServerlessRuntime()
    # 1st call: cold
    res1 = runtime.invoke([1.0, 2.0])
    assert res1["is_cold_start"] is True

    # 2nd call: warm
    res2 = runtime.invoke([1.0, 2.0])
    assert res2["is_cold_start"] is False
    assert res2["initialization_time_ms"] == 0.0
    assert res2["container_id"] == res1["container_id"]

    # 3rd call: warm
    res3 = runtime.invoke([3.0, 4.0])
    assert res3["is_cold_start"] is False
    assert res3["initialization_time_ms"] == 0.0

    metrics = runtime.get_metrics()
    assert metrics["total_invocations"] == 3
    assert metrics["cold_starts"] == 1
    assert metrics["warm_starts"] == 2


def test_serverless_reset_reverts_to_cold():
    runtime = ServerlessRuntime()
    runtime.invoke([1.0, 2.0])
    assert runtime.get_metrics()["total_invocations"] == 1

    reset_res = runtime.reset()
    assert reset_res["status"] == "reset_successful"
    assert reset_res["current_state"] == "COLD"

    metrics = runtime.get_metrics()
    assert metrics["total_invocations"] == 0
    assert metrics["cold_starts"] == 0
    assert metrics["warm_starts"] == 0
    assert metrics["runtime_state"] == "COLD"

    # Next invocation must be a cold start again
    res = runtime.invoke([1.0, 2.0])
    assert res["is_cold_start"] is True


def test_idle_timeout_teardown():
    # Use short idle timeout (0.15s) for fast deterministic test
    runtime = ServerlessRuntime(idle_timeout=0.15)
    res1 = runtime.invoke([1.0, 2.0])
    assert res1["is_cold_start"] is True
    cid1 = res1["container_id"]

    # Sleep longer than idle timeout
    time.sleep(0.20)

    # Next invocation should trigger teardown of previous container and new cold start
    res2 = runtime.invoke([1.0, 2.0])
    assert res2["is_cold_start"] is True
    assert res2["container_id"] != cid1

    metrics = runtime.get_metrics()
    assert metrics["cold_starts"] == 2
    event_names = [e["event"] for e in metrics["lifecycle_events"]]
    assert "IDLE_TIMEOUT_TEARDOWN" in event_names
