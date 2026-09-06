import os
import json
import time
import socket
import logging
import asyncio
from typing import List, Optional
from threading import Lock

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import grpc
import pika

from generated import inference_pb2, inference_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s"
)
logger = logging.getLogger("FastAPIGateway")

GRPC_WORKER_HOST = os.getenv("GRPC_WORKER_HOST", "localhost:50051")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
QUEUE_NAME = "batch_inference"

app = FastAPI(
    title="Distributed ML Inference Gateway",
    description="FastAPI Ingress Gateway for Sync gRPC and Async RabbitMQ ML Inference",
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

# In-memory metrics tracking
class MetricsManager:
    def __init__(self):
        self._lock = Lock()
        self.sync_requests = 0
        self.async_requests = 0
        self.total_sync_latency_ms = 0.0

    def record_sync(self, latency_ms: float):
        with self._lock:
            self.sync_requests += 1
            self.total_sync_latency_ms += latency_ms

    def record_async(self):
        with self._lock:
            self.async_requests += 1

    def get_stats(self):
        with self._lock:
            avg_latency = (
                round(self.total_sync_latency_ms / self.sync_requests, 2)
                if self.sync_requests > 0 else 0.0
            )
            return {
                "total_sync_requests": self.sync_requests,
                "total_async_requests": self.async_requests,
                "average_sync_latency_ms": avg_latency
            }

metrics = MetricsManager()


# Request Schemas
class PredictRequest(BaseModel):
    request_id: str = Field(..., example="req-001")
    input_tensor: List[float] = Field(..., example=[1.0, 2.0, 3.0, 4.0])
    model_name: str = Field(default="demo-model", example="demo-model")


# Health Check Helper Functions
def check_grpc_health() -> str:
    try:
        channel = grpc.insecure_channel(GRPC_WORKER_HOST)
        grpc.channel_ready_future(channel).result(timeout=1.0)
        channel.close()
        return "connected"
    except Exception:
        return "unavailable"


def check_rabbitmq_health() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex((RABBITMQ_HOST, RABBITMQ_PORT))
        sock.close()
        return "connected" if result == 0 else "unavailable"
    except Exception:
        return "unavailable"


@app.get("/health")
def get_health():
    grpc_status = check_grpc_health()
    rabbitmq_status = check_rabbitmq_health()
    
    # Batch consumer is active if RabbitMQ is reachable
    batch_consumer_status = "active" if rabbitmq_status == "connected" else "unavailable"

    return {
        "status": "healthy",
        "components": {
            "api_gateway": "healthy",
            "grpc_worker": grpc_status,
            "rabbitmq": rabbitmq_status,
            "batch_consumer": batch_consumer_status
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
        metrics.record_sync(gateway_latency_ms)

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


@app.post("/predict/async")
def predict_async(payload: PredictRequest):
    logger.info(f"Received Async Predict request ID: '{payload.request_id}'")
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                connection_attempts=2,
                retry_delay=1
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        message_body = json.dumps({
            "request_id": payload.request_id,
            "input_tensor": payload.input_tensor,
            "model_name": payload.model_name,
            "timestamp": time.time()
        })

        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2  # Make message persistent
            )
        )
        connection.close()

        metrics.record_async()

        return {
            "request_id": payload.request_id,
            "status": "enqueued",
            "queue": QUEUE_NAME,
            "processing_type": "asynchronous"
        }
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"RabbitMQ connection failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"RabbitMQ message broker unavailable at {RABBITMQ_HOST}:{RABBITMQ_PORT}"
        )
    except Exception as e:
        logger.error(f"Async prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@app.get("/stats")
def get_stats():
    return metrics.get_stats()


@app.websocket("/ws/signaling")
async def websocket_signaling(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket signaling client connected.")
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
                msg_type = msg.get("type", "unknown")
                logger.info(f"Received WebSocket signaling message type: '{msg_type}'")
                
                # Simple signaling response & acknowledgement
                response_ack = {
                    "status": "acknowledged",
                    "received_type": msg_type,
                    "timestamp": time.time(),
                    "payload": msg
                }
                await websocket.send_json(response_ack)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format", "received": data_text})
    except WebSocketDisconnect:
        logger.info("WebSocket signaling client disconnected.")
