import os
import time
import logging
from concurrent import futures
import grpc
import numpy as np

from generated import inference_pb2, inference_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s"
)
logger = logging.getLogger("InferenceWorker")


class InferenceServiceServicer(inference_pb2_grpc.InferenceServiceServicer):
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        logger.info(f"Initialized InferenceServiceServicer with WORKER_ID={self.worker_id}")

    def _process_tensor(self, input_tensor: list[float], model_name: str) -> tuple[list[float], float]:
        start_time = time.perf_counter()
        
        # NumPy simulated ML inference transformation
        arr = np.array(input_tensor, dtype=np.float32)
        
        # Determine coefficient multiplier based on model_name
        if "fast" in model_name.lower():
            coeff = 2.0
        elif "heavy" in model_name.lower():
            coeff = 0.5
        else:
            coeff = 1.5  # default model coefficient (e.g. [1, 2, 3, 4] -> [1.5, 3.0, 4.5, 6.0])
            
        transformed_arr = arr * coeff
        output_tensor = transformed_arr.tolist()
        
        # Measure execution time in milliseconds
        execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 4)
        return output_tensor, execution_time_ms

    def Predict(self, request: inference_pb2.InferenceRequest, context) -> inference_pb2.InferenceResponse:
        logger.info(f"[gRPC Predict] Request ID: '{request.request_id}', Model: '{request.model_name}', Tensor Size: {len(request.input_tensor)}")
        
        output_tensor, exec_time_ms = self._process_tensor(request.input_tensor, request.model_name)
        
        response = inference_pb2.InferenceResponse(
            request_id=request.request_id,
            worker_id=self.worker_id,
            output_tensor=output_tensor,
            execution_time_ms=exec_time_ms
        )
        logger.info(f"[gRPC Predict Success] Request ID: '{request.request_id}', Exec Time: {exec_time_ms} ms")
        return response

    def StreamPredict(self, request_iterator, context):
        logger.info("[gRPC StreamPredict] Started processing stream...")
        for request in request_iterator:
            logger.info(f"[gRPC Stream Element] Request ID: '{request.request_id}'")
            output_tensor, exec_time_ms = self._process_tensor(request.input_tensor, request.model_name)
            
            yield inference_pb2.InferenceResponse(
                request_id=request.request_id,
                worker_id=self.worker_id,
                output_tensor=output_tensor,
                execution_time_ms=exec_time_ms
            )


def serve():
    worker_id = os.getenv("WORKER_ID", "worker-node-alpha")
    grpc_port = os.getenv("GRPC_PORT", "50051")
    bind_address = f"0.0.0.0:{grpc_port}"

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inference_pb2_grpc.add_InferenceServiceServicer_to_server(
        InferenceServiceServicer(worker_id=worker_id),
        server
    )
    server.add_insecure_port(bind_address)
    logger.info(f"Starting gRPC Inference Worker '{worker_id}' on {bind_address}...")
    server.start()
    logger.info(f"gRPC Worker listening on {bind_address}")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC Worker...")
        server.stop(0)


if __name__ == "__main__":
    serve()
