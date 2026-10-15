# Distributed Machine Learning Inference Gateway

A unified, responsive, locally executable **Distributed ML Inference Gateway** demonstrating four core Distributed Systems concepts from Units III and IV built with Python, FastAPI, and HTML5/Tailwind CSS.

---

## 1. Project Overview & Distributed Systems Concepts

This project extends a machine learning inference gateway to demonstrate core theoretical and practical principles of distributed computing:

### Unit III: Synchronization
1. **Bully Election Algorithm** (`gateway/election.py`):
   - Dynamic coordinator election across nodes: **Node 100** (Worker Alpha), **Node 200** (Worker Beta), and **Node 300** (Worker Gamma).
   - Simulates `ELECTION`, `ANSWER` (`OK`), and `COORDINATOR` message exchanges.
   - Handles coordinator failure detection, cascading election rounds, and automatic coordinator reclamation upon higher-ID node recovery.
2. **Ricart–Agrawala Mutual Exclusion** (`gateway/mutual_exclusion.py`):
   - Distributed critical section coordination for a shared `"model-weights-update"` operation among three processes: **P1**, **P2**, and **P3**.
   - Employs Lamport logical clocks with timestamp update rule:  
     $$L = \max(L_{\text{local}}, L_{\text{received}}) + 1$$
   - Deterministic tie-breaking using priority tuples `(timestamp, process_id)`.
   - Implements `RELEASED`, `WANTED`, and `HELD` state transitions, deferred reply queues, and immediate peer replies without deadlocks or race conditions.

### Unit IV: Emerging Paradigms
3. **Distributed Web-Based System & Local Multi-Worker Cluster** (`gateway/worker_pool.py`):
   - Manages three logical inference workers: **Inference Worker 1**, **Inference Worker 2**, and **Inference Worker 3**.
   - Features round-robin request routing with automatic, health-aware failover.
   - Provides per-worker telemetry (total invocations, successes, failures, and execution latencies) and interactive node failure simulation.
4. **Serverless Architecture & Function-as-a-Service (FaaS)** (`gateway/serverless.py`):
   - Local FaaS runtime simulating micro-container lifecycle transitions: `COLD` $\to$ `INITIALIZING` $\to$ `WARM` $\to$ `EXECUTING` $\to$ `IDLE` $\to$ `TEARDOWN`.
   - Distinguishes cold start latency penalty (~220ms container spawn) from warm invocation reuse (~0.5ms).
   - Simulates memory consumption (128 MB base container allocation + dynamic tensor buffers).
   - Automatic idle timeout teardown (15s) and side-by-side architectural comparison with persistent worker pools.

---

## 2. Simulated vs. Genuine Distributed Behavior

> [!NOTE]
> **Local Simulation Disclosure**:
> - **Execution Environment**: All components run locally on a single machine using Python and a web browser.
> - **No Cloud / Container Overhead**: No Docker, Docker Compose, Kubernetes, AWS Lambda, or external orchestrators are required.
> - **In-Memory Models**: Processes, logical clocks, worker health states, and ephemeral serverless runtimes are modeled using thread-safe in-memory Python data structures.
> - **Authentic Logic**: Although execution is hosted within a single application process, the algorithms, message formats, logical clock synchronization, deferred queue mechanics, and round-robin failover logic operate strictly according to distributed systems theory.

---

## 3. Architecture

```text
+-----------------------------------------------------------------------------------+
|                        Unified Single-Page Dashboard UI                           |
|                             http://localhost:8000/                                |
|  [Header & Overview] [ML Inference] [Bully Election] [Ricart-Agrawala] [Workers] |
|                               [Serverless FaaS]                                   |
+-----------------------------------------------------------------------------------+
                                       |
                                       | HTTP REST
                                       v
+-----------------------------------------------------------------------------------+
|                            FastAPI Ingress Gateway                                |
|                               (gateway/app.py)                                    |
+-----------------------------------------------------------------------------------+
       |                    |                       |                     |
       v                    v                       v                     v
+--------------+   +-------------------+   +------------------+   +-----------------+
| Bully        |   | Ricart-Agrawala   |   | Multi-Worker     |   | Serverless FaaS |
| Election     |   | Mutual Exclusion  |   | Pool & Router    |   | Runtime Sim     |
| (election.py)|   | (mutual_exclusion)|   | (worker_pool.py) |   | (serverless.py) |
+--------------+   +-------------------+   +------------------+   +-----------------+
  Nodes: 100,200,300   P1, P2, P3            Worker 1, 2, 3         Cold/Warm Starts
  ELECTION/ANSWER      Lamport Clocks        Round-Robin Routing    Idle Timeout
  Coordinator Victory  Deferred Queues       Health Failover        128MB MicroVM
```

---

## 4. Technologies Used

- **Python 3.10+** (Tested on Python 3.12)
- **FastAPI** & **Uvicorn** (REST API & static single-page hosting)
- **NumPy** (Simulated ML inference matrix/tensor calculations)
- **Pytest** (Automated unit and concurrent integration test suite)
- **HTML5, Modern JavaScript, and Tailwind CSS** (Responsive dark-themed UI)

---

## 5. Project Structure

```text
ml-gateway/
├── gateway/
│   ├── __init__.py
│   ├── app.py                  # FastAPI ingress gateway & endpoint router
│   ├── election.py             # Bully election manager & node state
│   ├── mutual_exclusion.py     # Ricart-Agrawala mutual exclusion manager
│   ├── worker_pool.py          # Logical multi-worker pool & failover router
│   └── serverless.py           # Local FaaS runtime simulation
├── frontend/
│   ├── index.html              # Unified single-page dark-themed dashboard
│   └── app.js                  # Frontend client logic & live polling
├── tests/
│   ├── test_election.py        # Bully election unit tests
│   ├── test_ricart_agrawala.py # Ricart-Agrawala logical clock tests
│   ├── test_concurrent_cs.py   # Concurrent multi-threaded CS access tests
│   ├── test_serverless.py      # Cold/warm start & idle timeout tests
│   └── test_gateway.py         # Health, prediction, and worker failover tests
├── proto/
│   └── inference.proto         # Legacy gRPC Protocol Buffer definition
├── worker/
│   ├── __init__.py
│   └── worker.py               # Optional standalone gRPC worker
├── requirements.txt            # Python dependencies
└── README.md                   # Complete system documentation
```

---

## 6. Local Setup and Execution Instructions

### Prerequisites
- Python 3.10 or higher installed.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install pytest httpx
```

### 2. Run the Unified Gateway & Dashboard
Start the application with Uvicorn:
```bash
uvicorn gateway.app:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Access the Dashboard
Open your web browser and navigate to:
```text
http://localhost:8000/
```
*(Alternatively, if running the frontend via a separate HTTP server on `http://localhost:3000`, CORS is pre-configured to communicate seamlessly with port 8000).*

---

## 7. REST API Documentation

### System Overview & Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Gateway, worker pool, and gRPC component health check |
| `GET` | `/system/overview` | Aggregated dashboard header telemetry |

### Synchronous Inference Gateway
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/predict/sync` | Execute inference with round-robin routing and failover |

*Request Payload Example:*
```json
{
  "request_id": "req-001",
  "model_name": "demo-model",
  "input_tensor": [1.0, 2.0, 3.0, 4.0]
}
```

### Bully Election Algorithm (Unit III)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/election/status` | List nodes (100, 200, 300), availability, and current coordinator |
| `POST` | `/election/start` | Trigger Bully election (optional `initiator_id`) |
| `POST` | `/election/nodes/{id}/fail` | Mark node offline and trigger coordinator re-election |
| `POST` | `/election/nodes/{id}/recover` | Recover node; higher-ID node automatically reclaims leadership |
| `GET` | `/election/history` | Chronological audit log of ELECTION, ANSWER, and COORDINATOR messages |

### Ricart–Agrawala Mutual Exclusion (Unit III)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ricart-agrawala/status` | Process states, Lamport clocks, pending replies, deferred queues |
| `POST` | `/ricart-agrawala/request` | Request critical section for process (`{"process_id": "P1"}`) |
| `POST` | `/ricart-agrawala/release` | Release critical section and flush deferred replies (`{"process_id": "P1"}`) |
| `GET` | `/ricart-agrawala/history` | Event log of Lamport clock increments, requests, replies, and CS transitions |
| `POST` | `/ricart-agrawala/reset` | Reset mutual exclusion states |

### Multi-Worker Cluster (Unit IV)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/system/topology` | Logical cluster topology, gateway status, and round-robin index |
| `GET` | `/system/workers` | Telemetry for Worker 1, Worker 2, and Worker 3 |
| `POST` | `/system/workers/{id}/fail` | Simulate worker failure |
| `POST` | `/system/workers/{id}/recover` | Recover failed worker to healthy pool |

### Serverless Architecture & FaaS (Unit IV)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/serverless/invoke` | Invoke serverless function (measures cold vs. warm start latency) |
| `GET` | `/serverless/metrics` | Invocation counts, simulated memory, lifecycle history, comparison |
| `POST` | `/serverless/reset` | Revert serverless runtime state to COLD |

---

## 8. Dashboard Usage Guide

The single-page dashboard is vertically organized into 6 interactive sections:

1. **Header & System Overview**: Displays live application status, total requests, active logical workers, the elected Bully coordinator, and critical section occupancy.
2. **Inference Gateway**: Submit tensor arrays to the inference engine. Displays execution time, gateway latency, output tensor, and the assigned worker.
3. **Bully Election Algorithm**:
   - Inspect nodes 100, 200, and 300.
   - Click **Simulate Node Failure** on Node 300 to observe coordinator loss.
   - Click **Start Election** to observe ELECTION and ANSWER message cascades.
   - Click **Recover Node** on Node 300 to observe how higher-ID nodes reclaim coordinator status.
4. **Ricart–Agrawala Mutual Exclusion**:
   - Click **Request Critical Section** on **P1**; P1 immediately enters `HELD`.
   - Click **Request Critical Section** on **P2**; P2 enters `WANTED` and is deferred by P1.
   - Click **Release Critical Section** on **P1**; P1 flushes its deferred queue, and P2 automatically enters `HELD`.
5. **Distributed Web-Based System**:
   - Observe round-robin request distribution across Worker 1, Worker 2, and Worker 3.
   - Click **Simulate Worker Failure** on Worker 1; subsequent requests automatically fail over to Worker 2 and Worker 3.
   - If all workers are failed, the gateway returns HTTP 503 Service Unavailable.
6. **Serverless Architecture & FaaS**:
   - Click **Invoke Serverless Function**; the first invocation triggers a **Cold Start** (~220ms container initialization overhead).
   - Click again immediately; the runtime executes a **Warm Reuse** (0ms initialization overhead).
   - Wait 15 seconds without calls to watch the container trigger **Idle Timeout Teardown**.
   - Review the **Persistent vs. Serverless Comparison Table**.

---

## 9. Running Automated Tests

Run the complete test suite with Pytest:
```bash
python -m pytest tests -v
```

Expected output:
```text
tests/test_concurrent_cs.py::test_concurrent_critical_section_access PASSED
tests/test_election.py::test_initial_coordinator_is_highest_node PASSED
tests/test_election.py::test_election_initiated_by_lowest_node PASSED
tests/test_election.py::test_coordinator_failure_and_new_election PASSED
tests/test_election.py::test_cascading_failures_to_lowest_node PASSED
tests/test_election.py::test_higher_id_node_recovery_reclaims_leadership PASSED
tests/test_election.py::test_all_nodes_failed_election_handling PASSED
tests/test_election.py::test_election_history_audit_trail PASSED
tests/test_gateway.py::test_health_endpoint PASSED
tests/test_gateway.py::test_predict_sync_success PASSED
tests/test_gateway.py::test_worker_round_robin_distribution PASSED
tests/test_gateway.py::test_worker_failure_and_automatic_failover PASSED
tests/test_gateway.py::test_all_workers_unavailable_returns_503 PASSED
tests/test_gateway.py::test_worker_recovery PASSED
tests/test_gateway.py::test_system_topology_and_workers_endpoints PASSED
tests/test_gateway.py::test_system_overview_endpoint PASSED
tests/test_ricart_agrawala.py::test_initial_state PASSED
tests/test_ricart_agrawala.py::test_single_process_cs_entry_and_clock_update PASSED
tests/test_ricart_agrawala.py::test_deferred_reply_when_cs_held PASSED
tests/test_ricart_agrawala.py::test_release_cs_flushes_deferred_reply_and_transfers_cs PASSED
tests/test_ricart_agrawala.py::test_priority_tie_breaking_timestamp_and_pid PASSED
tests/test_serverless.py::test_first_invocation_is_cold_start PASSED
tests/test_serverless.py::test_subsequent_invocations_reuse_warm_container PASSED
tests/test_serverless.py::test_serverless_reset_reverts_to_cold PASSED
tests/test_serverless.py::test_idle_timeout_teardown PASSED

======================== 25 passed in ~4.5s ========================
```

---

## 10. Known Limitations

- **Single Host Simulation**: Because Docker and multi-VM orchestration are intentionally omitted to permit local execution on one computer, network partitions and true socket delays are simulated in-process.
- **Simulated Memory Footprint**: The serverless RAM metric reflects container memory provisioning (128 MB microVM allocation) rather than operating-system process RSS.
- **In-Memory Volatility**: Algorithm states and telemetry reset when the FastAPI server process is restarted.
