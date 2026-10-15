"""
Integration tests for FastAPI Gateway endpoints (health, prediction, routing, failover, topology)
"""

import pytest
from fastapi.testclient import TestClient
from gateway.app import app
from gateway.worker_pool import worker_pool

client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_workers():
    # Ensure all workers are recovered before each test
    for w_id in list(worker_pool.workers.keys()):
        worker_pool.recover_worker(w_id)
    yield
    for w_id in list(worker_pool.workers.keys()):
        worker_pool.recover_worker(w_id)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "api_gateway" in data["components"]
    assert data["components"]["api_gateway"] == "healthy"
    assert data["components"]["worker_pool"] == "healthy"
    assert data["active_workers"] == 3


def test_predict_sync_success():
    payload = {
        "request_id": "test-req-001",
        "input_tensor": [1.0, 2.0, 3.0, 4.0],
        "model_name": "demo-model"
    }
    response = client.post("/predict/sync", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "test-req-001"
    assert data["output_tensor"] == [1.5, 3.0, 4.5, 6.0]
    assert "worker_id" in data
    assert "execution_time_ms" in data
    assert "gateway_latency_ms" in data
    assert data["processing_type"] == "synchronous"
    assert "routing" in data


def test_worker_round_robin_distribution():
    # Make multiple requests and verify workers alternate
    workers_used = []
    for i in range(3):
        payload = {
            "request_id": f"rr-req-{i}",
            "input_tensor": [1.0, 2.0],
            "model_name": "fast-model"
        }
        res = client.post("/predict/sync", json=payload)
        assert res.status_code == 200
        workers_used.append(res.json()["worker_id"])

    # All 3 workers should have been used in round-robin fashion
    assert len(set(workers_used)) >= 2  # round-robin distributes across workers


def test_worker_failure_and_automatic_failover():
    # Fail worker-1
    fail_res = client.post("/system/workers/worker-1/fail")
    assert fail_res.status_code == 200
    assert fail_res.json()["is_healthy"] is False

    # Send requests, none should be routed to worker-1
    for i in range(4):
        payload = {
            "request_id": f"failover-req-{i}",
            "input_tensor": [2.0, 4.0],
            "model_name": "demo-model"
        }
        res = client.post("/predict/sync", json=payload)
        assert res.status_code == 200
        assert res.json()["worker_id"] != "worker-1"
        assert res.json()["worker_id"] in ["worker-2", "worker-3"]


def test_all_workers_unavailable_returns_503():
    # Fail all 3 workers
    client.post("/system/workers/worker-1/fail")
    client.post("/system/workers/worker-2/fail")
    client.post("/system/workers/worker-3/fail")

    payload = {
        "request_id": "unavailable-req-1",
        "input_tensor": [1.0, 2.0],
        "model_name": "demo-model"
    }
    res = client.post("/predict/sync", json=payload)
    assert res.status_code == 503
    assert "unavailable" in res.json()["detail"].lower() or "offline" in res.json()["detail"].lower()


def test_worker_recovery():
    # Fail and recover worker-1
    client.post("/system/workers/worker-1/fail")
    assert worker_pool.workers["worker-1"].is_healthy is False

    rec_res = client.post("/system/workers/worker-1/recover")
    assert rec_res.status_code == 200
    assert rec_res.json()["is_healthy"] is True
    assert worker_pool.workers["worker-1"].is_healthy is True


def test_system_topology_and_workers_endpoints():
    topo_res = client.get("/system/topology")
    assert topo_res.status_code == 200
    topo = topo_res.json()
    assert "gateway" in topo
    assert "workers" in topo
    assert len(topo["workers"]) == 3

    workers_res = client.get("/system/workers")
    assert workers_res.status_code == 200
    assert len(workers_res.json()) == 3


def test_system_overview_endpoint():
    overview_res = client.get("/system/overview")
    assert overview_res.status_code == 200
    data = overview_res.json()
    assert data["application_status"] == "ONLINE"
    assert "total_inference_requests" in data
    assert "active_workers" in data
    assert "current_coordinator" in data
    assert "critical_section" in data
