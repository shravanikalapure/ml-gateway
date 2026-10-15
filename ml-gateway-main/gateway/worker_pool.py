"""
Distributed Web-Based System & Local Multi-Worker Simulation (Unit IV: Emerging Paradigms)

Simulates three logical inference workers:
- Inference Worker 1 (worker-1)
- Inference Worker 2 (worker-2)
- Inference Worker 3 (worker-3)

These workers run as local in-memory Python instances on a single machine.
Demonstrates:
- Round-robin request routing
- Health-aware worker selection
- Automatic failover to remaining available workers
- Per-worker telemetry (total, success, failure, latency)
- Dynamic worker failure and recovery controls
- Integrated ML inference execution adapter using the project's NumPy model
"""

import time
import threading
from typing import Dict, List, Optional, Any, Tuple
import numpy as np


class LogicalInferenceWorker:
    def __init__(self, worker_id: str, name: str):
        self.worker_id = worker_id
        self.name = name
        self.is_healthy: bool = True
        self.status: str = "HEALTHY"  # HEALTHY, FAILED

        # Telemetry
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.last_latency_ms: float = 0.0
        self.avg_latency_ms: float = 0.0
        self.total_latency_ms: float = 0.0

    def fail(self):
        self.is_healthy = False
        self.status = "FAILED"

    def recover(self):
        self.is_healthy = True
        self.status = "HEALTHY"

    def predict(self, input_tensor: List[float], model_name: str) -> Tuple[List[float], float]:
        """
        Execute ML inference using NumPy transformation (same mathematical logic as worker/worker.py).
        """
        if not self.is_healthy:
            self.failed_requests += 1
            self.total_requests += 1
            raise RuntimeError(f"Worker '{self.worker_id}' is unhealthy/offline.")

        start_time = time.perf_counter()

        arr = np.array(input_tensor, dtype=np.float32)

        # Model multiplier
        if "fast" in model_name.lower():
            coeff = 2.0
        elif "heavy" in model_name.lower():
            coeff = 0.5
        else:
            coeff = 1.5

        transformed_arr = arr * coeff
        output_tensor = transformed_arr.tolist()

        exec_time_ms = round((time.perf_counter() - start_time) * 1000.0, 4)

        # Update telemetry
        self.total_requests += 1
        self.successful_requests += 1
        self.last_latency_ms = exec_time_ms
        self.total_latency_ms += exec_time_ms
        self.avg_latency_ms = round(self.total_latency_ms / self.successful_requests, 4)

        return output_tensor, exec_time_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "name": self.name,
            "is_healthy": self.is_healthy,
            "status": self.status,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "last_latency_ms": self.last_latency_ms,
            "avg_latency_ms": self.avg_latency_ms
        }


class WorkerPool:
    def __init__(self):
        self._lock = threading.Lock()
        self.workers: Dict[str, LogicalInferenceWorker] = {
            "worker-1": LogicalInferenceWorker("worker-1", "Inference Worker 1"),
            "worker-2": LogicalInferenceWorker("worker-2", "Inference Worker 2"),
            "worker-3": LogicalInferenceWorker("worker-3", "Inference Worker 3"),
        }
        self.worker_keys = ["worker-1", "worker-2", "worker-3"]
        self.round_robin_index = 0
        self.total_gateway_requests = 0
        self.routing_history: List[Dict[str, Any]] = []

    def get_topology(self) -> Dict[str, Any]:
        with self._lock:
            healthy_count = sum(1 for w in self.workers.values() if w.is_healthy)
            return {
                "system_type": "Logical Multi-Worker Cluster (Local Simulation)",
                "note": "All workers execute locally as in-memory Python instances on one host.",
                "gateway": {
                    "host": "localhost:8000",
                    "status": "ONLINE",
                    "total_requests": self.total_gateway_requests,
                    "active_workers": healthy_count,
                    "total_workers": len(self.workers),
                    "routing_strategy": "Round-Robin with Automatic Health-Aware Failover"
                },
                "workers": [w.to_dict() for w in self.workers.values()],
                "current_rr_index": self.round_robin_index
            }

    def get_workers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [w.to_dict() for w in self.workers.values()]

    def fail_worker(self, worker_id: str) -> Dict[str, Any]:
        with self._lock:
            if worker_id not in self.workers:
                raise ValueError(f"Unknown worker ID: {worker_id}")
            worker = self.workers[worker_id]
            worker.fail()
            self._record_routing_event(
                request_id="SYS-CTRL",
                selected_worker=worker_id,
                status="FAILED_MANUALLY",
                latency_ms=0.0,
                message=f"Worker {worker_id} ({worker.name}) was manually marked as FAILED."
            )
            return worker.to_dict()

    def recover_worker(self, worker_id: str) -> Dict[str, Any]:
        with self._lock:
            if worker_id not in self.workers:
                raise ValueError(f"Unknown worker ID: {worker_id}")
            worker = self.workers[worker_id]
            worker.recover()
            self._record_routing_event(
                request_id="SYS-CTRL",
                selected_worker=worker_id,
                status="RECOVERED_MANUALLY",
                latency_ms=0.0,
                message=f"Worker {worker_id} ({worker.name}) was recovered to HEALTHY state."
            )
            return worker.to_dict()

    def _record_routing_event(
        self,
        request_id: str,
        selected_worker: str,
        status: str,
        latency_ms: float,
        message: str,
        failover_attempts: int = 0
    ):
        event = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S", time.localtime()),
            "request_id": request_id,
            "selected_worker": selected_worker,
            "status": status,
            "latency_ms": latency_ms,
            "failover_attempts": failover_attempts,
            "message": message
        }
        self.routing_history.append(event)
        if len(self.routing_history) > 100:
            self.routing_history.pop(0)

    def route_and_predict(
        self,
        request_id: str,
        input_tensor: List[float],
        model_name: str
    ) -> Dict[str, Any]:
        """
        Routes the inference request to an available worker using round-robin.
        If the selected worker is unhealthy, automatically fails over to the next healthy worker.
        If all workers are unhealthy, raises a RuntimeError.
        """
        start_gw_time = time.perf_counter()

        with self._lock:
            self.total_gateway_requests += 1

            total_workers = len(self.worker_keys)
            healthy_workers = [w for w in self.workers.values() if w.is_healthy]

            if not healthy_workers:
                self._record_routing_event(
                    request_id=request_id,
                    selected_worker="NONE",
                    status="SERVICE_UNAVAILABLE",
                    latency_ms=0.0,
                    message="All inference workers are unavailable. Inference rejected."
                )
                raise RuntimeError("All inference workers are currently offline/unhealthy.")

            # Attempt round-robin with failover
            attempts = 0
            selected_worker = None

            while attempts < total_workers:
                idx = self.round_robin_index % total_workers
                candidate_id = self.worker_keys[idx]
                candidate = self.workers[candidate_id]
                self.round_robin_index = (self.round_robin_index + 1) % total_workers
                attempts += 1

                if candidate.is_healthy:
                    selected_worker = candidate
                    break

            if not selected_worker:
                # Fallback to any healthy worker
                selected_worker = healthy_workers[0]

        # Execute prediction outside of lock so other requests are not blocked
        try:
            output_tensor, exec_time_ms = selected_worker.predict(input_tensor, model_name)
            gw_latency_ms = round((time.perf_counter() - start_gw_time) * 1000.0, 2)

            with self._lock:
                self._record_routing_event(
                    request_id=request_id,
                    selected_worker=selected_worker.worker_id,
                    status="SUCCESS",
                    latency_ms=gw_latency_ms,
                    failover_attempts=attempts - 1,
                    message=f"Routed request {request_id} to {selected_worker.name} (failovers: {attempts - 1})."
                )

            return {
                "request_id": request_id,
                "worker_id": selected_worker.worker_id,
                "worker_name": selected_worker.name,
                "output_tensor": output_tensor,
                "execution_time_ms": exec_time_ms,
                "gateway_latency_ms": gw_latency_ms,
                "processing_type": "synchronous",
                "routing": {
                    "strategy": "round-robin-with-failover",
                    "failover_attempts": attempts - 1,
                    "worker_healthy": selected_worker.is_healthy
                }
            }
        except Exception as e:
            gw_latency_ms = round((time.perf_counter() - start_gw_time) * 1000.0, 2)
            with self._lock:
                self._record_routing_event(
                    request_id=request_id,
                    selected_worker=selected_worker.worker_id if selected_worker else "UNKNOWN",
                    status="EXECUTION_FAILED",
                    latency_ms=gw_latency_ms,
                    message=f"Inference execution failed on worker: {str(e)}"
                )
            raise


# Global singleton instance for application use
worker_pool = WorkerPool()
