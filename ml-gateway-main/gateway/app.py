import os
import time
import logging
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import grpc

from generated import inference_pb2, inference_pb2_grpc
from gateway.election import bully_election_manager
from gateway.mutual_exclusion import ricart_agrawala_manager
from gateway.worker_pool import worker_pool
from gateway.serverless import serverless_runtime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s"
)
logger = logging.getLogger("FastAPIGateway")

GRPC_WORKER_HOST = os.getenv("GRPC_WORKER_HOST", "localhost:50051")

app = FastAPI(
    title="Distributed ML Inference Gateway",
    description="FastAPI Gateway with Bully Election, Ricart–Agrawala Mutual Exclusion, Multi-Worker Cluster, and Serverless FaaS Simulation",
    version="2.0.0"
)

# Enable CORS for http://localhost:3000 and standard development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Schemas
class PredictRequest(BaseModel):
    request_id: str = Field(default="req-001", json_schema_extra={"example": "req-001"})
    input_tensor: List[float] = Field(..., json_schema_extra={"example": [1.0, 2.0, 3.0, 4.0]})
    model_name: str = Field(default="demo-model", json_schema_extra={"example": "demo-model"})


class ElectionStartRequest(BaseModel):
    initiator_id: Optional[int] = Field(default=None, json_schema_extra={"example": 100})


class ProcessCSRequest(BaseModel):
    process_id: str = Field(..., json_schema_extra={"example": "P1"})


class ServerlessInvokeRequest(BaseModel):
    input_tensor: List[float] = Field(default=[1.0, 2.0, 3.0, 4.0, 5.0], json_schema_extra={"example": [1.0, 2.0, 3.0, 4.0, 5.0]})
    model_name: str = Field(default="demo-model", json_schema_extra={"example": "demo-model"})


# Health Check Helper
def check_grpc_health() -> str:
    try:
        channel = grpc.insecure_channel(GRPC_WORKER_HOST)
        grpc.channel_ready_future(channel).result(timeout=0.5)
        channel.close()
        return "connected"
    except Exception:
        return "unavailable"


# -------------------------------------------------------------------------
# 1. System Health & Unified Overview
# -------------------------------------------------------------------------

@app.get("/health")
def get_health():
    grpc_status = check_grpc_health()
    workers = worker_pool.get_workers()
    active_workers = sum(1 for w in workers if w["is_healthy"])

    return {
        "status": "healthy" if active_workers > 0 else "degraded",
        "components": {
            "api_gateway": "healthy",
            "grpc_worker": grpc_status,
            "worker_pool": "healthy" if active_workers > 0 else "unavailable"
        },
        "active_workers": active_workers,
        "total_workers": len(workers)
    }


@app.get("/system/overview")
def get_system_overview():
    """Aggregated status for the dashboard header."""
    election_status = bully_election_manager.get_status()
    ra_status = ricart_agrawala_manager.get_status()
    workers = worker_pool.get_workers()
    active_workers = sum(1 for w in workers if w["is_healthy"])
    faas_metrics = serverless_runtime.get_metrics()

    return {
        "application_status": "ONLINE",
        "total_inference_requests": worker_pool.total_gateway_requests,
        "active_workers": active_workers,
        "total_workers": len(workers),
        "current_coordinator": {
            "id": election_status["coordinator_id"],
            "name": election_status["coordinator_name"]
        },
        "critical_section": {
            "occupied": ra_status["cs_occupied"],
            "holder": ra_status["current_cs_holder"],
            "resource": ra_status["resource_name"]
        },
        "serverless_runtime": {
            "state": faas_metrics["runtime_state"],
            "total_invocations": faas_metrics["total_invocations"]
        }
    }


# -------------------------------------------------------------------------
# 2. Synchronous Inference Gateway with Multi-Worker Routing & Failover
# -------------------------------------------------------------------------

@app.post("/predict/sync")
def predict_sync(payload: PredictRequest):
    logger.info(f"Received Sync Predict request ID: '{payload.request_id}' with tensor len: {len(payload.input_tensor)}")
    try:
        # Route through the local multi-worker pool with round-robin and health-aware failover
        result = worker_pool.route_and_predict(
            request_id=payload.request_id,
            input_tensor=payload.input_tensor,
            model_name=payload.model_name
        )
        return result
    except RuntimeError as e:
        logger.error(f"Routing/Worker error for request '{payload.request_id}': {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Sync prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# -------------------------------------------------------------------------
# 3. Bully Election Algorithm Endpoints (Unit III: Synchronization)
# -------------------------------------------------------------------------

@app.get("/election/status")
def get_election_status():
    return bully_election_manager.get_status()


@app.post("/election/start")
def start_election(request: Optional[ElectionStartRequest] = None):
    try:
        initiator_id = request.initiator_id if request else None
        result = bully_election_manager.start_election(initiator_id=initiator_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/election/nodes/{node_id}/fail")
def fail_election_node(node_id: int):
    try:
        return bully_election_manager.fail_node(node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/election/nodes/{node_id}/recover")
def recover_election_node(node_id: int):
    try:
        return bully_election_manager.recover_node(node_id, auto_elect=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/election/history")
def get_election_history(limit: int = 50):
    return bully_election_manager.get_history(limit=limit)


# -------------------------------------------------------------------------
# 4. Ricart–Agrawala Mutual Exclusion Endpoints (Unit III: Synchronization)
# -------------------------------------------------------------------------

@app.get("/ricart-agrawala/status")
def get_ricart_agrawala_status():
    return ricart_agrawala_manager.get_status()


@app.post("/ricart-agrawala/request")
def request_critical_section(req: ProcessCSRequest):
    try:
        result = ricart_agrawala_manager.request_cs(req.process_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ricart-agrawala/release")
def release_critical_section(req: ProcessCSRequest):
    try:
        result = ricart_agrawala_manager.release_cs(req.process_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/ricart-agrawala/history")
def get_ricart_agrawala_history(limit: int = 50):
    return ricart_agrawala_manager.get_history(limit=limit)


@app.post("/ricart-agrawala/reset")
def reset_ricart_agrawala():
    ricart_agrawala_manager.reset()
    return {"status": "reset_successful"}


# -------------------------------------------------------------------------
# 5. Distributed Web-Based System & Worker Pool Endpoints (Unit IV)
# -------------------------------------------------------------------------

@app.get("/system/topology")
def get_system_topology():
    return worker_pool.get_topology()


@app.get("/system/workers")
def get_system_workers():
    return worker_pool.get_workers()


@app.post("/system/workers/{worker_id}/fail")
def fail_system_worker(worker_id: str):
    try:
        return worker_pool.fail_worker(worker_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/system/workers/{worker_id}/recover")
def recover_system_worker(worker_id: str):
    try:
        return worker_pool.recover_worker(worker_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------------------------------------------------------
# 6. Serverless Architecture & FaaS Endpoints (Unit IV)
# -------------------------------------------------------------------------

@app.post("/serverless/invoke")
def invoke_serverless_function(req: ServerlessInvokeRequest):
    return serverless_runtime.invoke(
        input_tensor=req.input_tensor,
        model_name=req.model_name
    )


@app.get("/serverless/metrics")
def get_serverless_metrics():
    return serverless_runtime.get_metrics()


@app.post("/serverless/reset")
def reset_serverless_runtime():
    return serverless_runtime.reset()


# -------------------------------------------------------------------------
# 7. Mount Frontend Static Files for Direct Browser Access
# -------------------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
