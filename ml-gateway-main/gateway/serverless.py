"""
Serverless Architecture & Function-as-a-Service (FaaS) Simulation (Unit IV: Emerging Paradigms)

Simulates a local FaaS function runtime demonstrating:
- Cold starts vs warm invocations
- Container / runtime initialization latency
- Actual execution duration measurement
- Runtime reuse
- Transparent simulated memory consumption (clearly marked as simulated, not OS memory)
- Idle timeout with automatic container teardown
- Lifecycle event logging
- Comparative analytics: Persistent Dedicated Workers vs On-Demand FaaS Execution
"""

import time
import threading
from typing import Dict, List, Optional, Any
import numpy as np


class ServerlessRuntime:
    DEFAULT_IDLE_TIMEOUT_SEC = 15.0
    SIMULATED_COLD_INIT_MS = 220.0  # Simulated container initialization latency in ms
    BASE_MEMORY_MB = 128.0          # Base simulated container memory allocation in MB

    def __init__(self, idle_timeout: float = DEFAULT_IDLE_TIMEOUT_SEC):
        self._lock = threading.Lock()
        self.idle_timeout = idle_timeout
        self.is_initialized: bool = False
        self.state: str = "COLD"  # COLD, INITIALIZING, WARM, EXECUTING, TORN_DOWN
        self.last_invocation_time: Optional[float] = None
        self.container_id: Optional[str] = None

        # Metrics
        self.total_invocations: int = 0
        self.cold_starts: int = 0
        self.warm_starts: int = 0
        self.total_init_time_ms: float = 0.0
        self.total_exec_time_ms: float = 0.0
        self.last_init_time_ms: float = 0.0
        self.last_exec_time_ms: float = 0.0
        self.simulated_memory_mb: float = 0.0

        self.lifecycle_events: List[Dict[str, Any]] = []

        self._record_lifecycle_event(
            event="SYSTEM_INIT",
            details="Serverless FaaS runtime initialized in COLD state (no active container)."
        )

    def _record_lifecycle_event(self, event: str, details: str, is_cold: bool = False):
        entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S", time.localtime()),
            "event": event,
            "is_cold_start": is_cold,
            "container_id": self.container_id,
            "state": self.state,
            "details": details
        }
        self.lifecycle_events.append(entry)
        if len(self.lifecycle_events) > 100:
            self.lifecycle_events.pop(0)

    def _check_idle_timeout_locked(self):
        """Checks if container has exceeded idle timeout and tears it down if necessary."""
        if self.is_initialized and self.last_invocation_time is not None:
            idle_duration = time.time() - self.last_invocation_time
            if idle_duration > self.idle_timeout:
                old_cid = self.container_id
                self.is_initialized = False
                self.state = "TORN_DOWN"
                self.container_id = None
                self.simulated_memory_mb = 0.0
                self._record_lifecycle_event(
                    event="IDLE_TIMEOUT_TEARDOWN",
                    details=f"Container {old_cid} exceeded idle timeout of {self.idle_timeout}s ({round(idle_duration, 1)}s idle). Torn down to reclaim resources."
                )

    def invoke(
        self,
        input_tensor: List[float],
        model_name: str = "demo-model"
    ) -> Dict[str, Any]:
        """
        Invokes the simulated serverless function.
        Handles cold start initialization vs warm execution reuse.
        """
        start_total = time.perf_counter()

        with self._lock:
            # Check if idle timeout tore down existing container
            self._check_idle_timeout_locked()

            is_cold = not self.is_initialized
            init_time_ms = 0.0

            if is_cold:
                self.state = "INITIALIZING"
                self.container_id = f"faas-inst-{int(time.time() * 1000) % 100000:05d}"
                self._record_lifecycle_event(
                    event="CONTAINER_SPAWN",
                    details=f"Cold start detected: Spawning new micro-container '{self.container_id}'.",
                    is_cold=True
                )

                # Simulate cold start container spin-up and model loading latency
                time.sleep(self.SIMULATED_COLD_INIT_MS / 1000.0)
                init_time_ms = self.SIMULATED_COLD_INIT_MS

                self.is_initialized = True
                self.cold_starts += 1
                self.total_init_time_ms += init_time_ms
                self.last_init_time_ms = init_time_ms
                self.state = "WARM"
            else:
                self.warm_starts += 1
                init_time_ms = 0.0
                self.last_init_time_ms = 0.0
                self._record_lifecycle_event(
                    event="WARM_INVOCATION",
                    details=f"Reusing warm container '{self.container_id}' (zero container initialization overhead).",
                    is_cold=False
                )

            self.state = "EXECUTING"
            self.total_invocations += 1

        # Execution phase (using NumPy ML transformation)
        start_exec = time.perf_counter()
        arr = np.array(input_tensor, dtype=np.float32)

        if "fast" in model_name.lower():
            coeff = 2.0
        elif "heavy" in model_name.lower():
            coeff = 0.5
        else:
            coeff = 1.5

        transformed_arr = arr * coeff
        output_tensor = transformed_arr.tolist()
        exec_time_ms = round((time.perf_counter() - start_exec) * 1000.0, 4)

        # Simulated memory model: base 128MB + dynamic tensor memory
        simulated_tensor_mb = round((len(input_tensor) * 4 * 2) / (1024 * 1024) + 2.5, 2)
        total_simulated_mb = self.BASE_MEMORY_MB + simulated_tensor_mb

        total_duration_ms = round((time.perf_counter() - start_total) * 1000.0, 2)

        with self._lock:
            self.state = "WARM"
            self.last_invocation_time = time.time()
            self.last_exec_time_ms = exec_time_ms
            self.total_exec_time_ms += exec_time_ms
            self.simulated_memory_mb = total_simulated_mb

            self._record_lifecycle_event(
                event="FUNCTION_COMPLETE",
                details=f"Function execution completed in {exec_time_ms} ms (Total including init: {total_duration_ms} ms)."
            )

        return {
            "function_name": "predict-faas",
            "container_id": self.container_id,
            "is_cold_start": is_cold,
            "initialization_time_ms": init_time_ms,
            "execution_time_ms": exec_time_ms,
            "total_duration_ms": total_duration_ms,
            "output_tensor": output_tensor,
            "simulated_memory": {
                "container_base_mb": self.BASE_MEMORY_MB,
                "dynamic_buffer_mb": simulated_tensor_mb,
                "total_simulated_mb": total_simulated_mb,
                "disclaimer": "Simulated FaaS container memory allocation, not OS process RSS"
            },
            "runtime_state": self.state
        }

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            self._check_idle_timeout_locked()

            avg_init_ms = (
                round(self.total_init_time_ms / self.cold_starts, 2)
                if self.cold_starts > 0 else 0.0
            )
            avg_exec_ms = (
                round(self.total_exec_time_ms / self.total_invocations, 2)
                if self.total_invocations > 0 else 0.0
            )

            idle_seconds_left = 0.0
            if self.is_initialized and self.last_invocation_time is not None:
                idle_elapsed = time.time() - self.last_invocation_time
                idle_seconds_left = max(0.0, round(self.idle_timeout - idle_elapsed, 1))

            return {
                "runtime_state": self.state,
                "container_id": self.container_id,
                "is_initialized": self.is_initialized,
                "idle_timeout_seconds": self.idle_timeout,
                "idle_seconds_until_teardown": idle_seconds_left,
                "total_invocations": self.total_invocations,
                "cold_starts": self.cold_starts,
                "warm_starts": self.warm_starts,
                "last_init_time_ms": self.last_init_time_ms,
                "last_exec_time_ms": self.last_exec_time_ms,
                "avg_init_time_ms": avg_init_ms,
                "avg_exec_time_ms": avg_exec_ms,
                "simulated_memory_mb": self.simulated_memory_mb,
                "lifecycle_events": list(reversed(self.lifecycle_events[-30:])),
                "comparison": self.get_comparison()
            }

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self.is_initialized = False
            self.state = "COLD"
            self.last_invocation_time = None
            self.container_id = None
            self.total_invocations = 0
            self.cold_starts = 0
            self.warm_starts = 0
            self.total_init_time_ms = 0.0
            self.total_exec_time_ms = 0.0
            self.last_init_time_ms = 0.0
            self.last_exec_time_ms = 0.0
            self.simulated_memory_mb = 0.0

            self._record_lifecycle_event(
                event="RUNTIME_RESET",
                details="FaaS runtime and telemetry were explicitly reset. State reverted to COLD."
            )

            return {
                "status": "reset_successful",
                "current_state": self.state
            }

    @staticmethod
    def get_comparison() -> Dict[str, Any]:
        return {
            "dimensions": [
                {
                    "attribute": "Startup Latency",
                    "persistent_cluster": "Zero startup latency (~0.5ms inference)",
                    "serverless_faas": "Cold start penalty (~220ms init on spin-up), warm reuse (~0.5ms)"
                },
                {
                    "attribute": "Resource Provisioning",
                    "persistent_cluster": "Static pre-warmed worker pool (dedicated local workers)",
                    "serverless_faas": "On-demand ephemeral runtime with idle timeout teardown"
                },
                {
                    "attribute": "Memory & Cost Footprint",
                    "persistent_cluster": "Persistent memory allocation (workers remain resident in RAM)",
                    "serverless_faas": "Zero memory & zero cost when idle; pay/allocate only per millisecond"
                },
                {
                    "attribute": "Scaling Model",
                    "persistent_cluster": "Fixed capacity (round-robin among provisioned workers)",
                    "serverless_faas": "Elastic auto-scaling per request invocation"
                },
                {
                    "attribute": "Ideal Workload",
                    "persistent_cluster": "Steady, high-throughput, latency-critical inference pipelines",
                    "serverless_faas": "Burst-heavy, sporadic, or cost-sensitive intermittent tasks"
                }
            ],
            "simulation_note": "This simulation runs entirely locally on one computer. Real FaaS clouds (AWS Lambda, Google Cloud Functions) execute microVMs across physical data centers."
        }


# Global singleton instance for application use
serverless_runtime = ServerlessRuntime()
