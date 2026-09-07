import os
import time
import logging
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import grpc

from generated import inference_pb2, inference_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s"
)
logger = logging.getLogger("FastAPIGateway")

GRPC_WORKER_HOST = os.getenv("GRPC_WORKER_HOST", "localhost:50051")

app = FastAPI(
    title="Distributed ML Inference Gateway",
    description="FastAPI Ingress Gateway for Synchronous gRPC ML Inference",
    version="1.0.0"
)

# Enable CORS for http://localhost:3000 and standard development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Schema
class PredictRequest(BaseModel):
    request_id: str = Field(..., example="req-001")
    input_tensor: List[float] = Field(..., example=[1.0, 2.0, 3.0, 4.0])
    model_name: str = Field(default="demo-model", example="demo-model")


# Health Check Helper
def check_grpc_health() -> str:
    try:
        channel = grpc.insecure_channel(GRPC_WORKER_HOST)
        grpc.channel_ready_future(channel).result(timeout=1.0)
        channel.close()
        return "connected"
    except Exception:
        return "unavailable"


@app.get("/health")
def get_health():
    grpc_status = check_grpc_health()

    return {
        "status": "healthy",
        "components": {
            "api_gateway": "healthy",
            "grpc_worker": grpc_status
        }
    }


@app.post("/predict/sync")
def predict_sync(payload: PredictRequest):
    start_time = time.perf_counter()
    logger.info(f"Received Sync Predict request ID: '{payload.request_id}'")

    try:
        # Create gRPC channel and stub
        channel = grpc.insecure_channel(GRPC_WORKER_HOST)
        stub = inference_pb2_grpc.InferenceServiceStub(channel)

        request = inference_pb2.InferenceRequest(
            request_id=payload.request_id,
            input_tensor=payload.input_tensor,
            model_name=payload.model_name
        )

        # Call worker with timeout
        response = stub.Predict(request, timeout=5.0)
        channel.close()

        gateway_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return {
            "request_id": response.request_id,
            "worker_id": response.worker_id,
            "output_tensor": list(response.output_tensor),
            "execution_time_ms": response.execution_time_ms,
            "gateway_latency_ms": gateway_latency_ms,
            "processing_type": "synchronous"
        }
    except grpc.RpcError as e:
        logger.error(f"gRPC call failed for request '{payload.request_id}': {e.details()}")
        raise HTTPException(
            status_code=503,
            detail=f"gRPC Worker unavailable at {GRPC_WORKER_HOST}. Error: {e.details()}"
        )
    except Exception as e:
        logger.error(f"Sync prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
