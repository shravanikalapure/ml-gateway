# Distributed Machine Learning Inference Gateway

A simplified, high-performance **Distributed ML Inference Gateway** built with Python, FastAPI, gRPC, and Protocol Buffers.

---

## 1. Project Overview

This project demonstrates a core distributed system architecture for Machine Learning (ML) inference. It provides an HTTP REST ingress API Gateway that translates client requests into high-speed binary gRPC calls to a dedicated ML inference worker node.

---

## 2. Architecture

```text
Frontend (localhost:3000)
        |
        | HTTP REST
        v
FastAPI Gateway (localhost:8000)
        |
        | gRPC
        v
gRPC Worker (localhost:50051)
        |
        v
  ML Inference
```

---

## 3. Technologies Used

- **Python 3.10+**
- **FastAPI** & **Uvicorn**
- **gRPC (`grpcio`, `grpcio-tools`)** & **Protocol Buffers (`protobuf`)**
- **NumPy**
- **HTML5 / JavaScript / Tailwind CSS CDN**

---

## 4. Project Structure

```text
ml-gateway/
├── proto/
│   └── inference.proto         # Protocol Buffer definition
├── generated/
│   ├── __init__.py
│   ├── inference_pb2.py        # Generated protobuf data structures
│   └── inference_pb2_grpc.py   # Generated gRPC client/server stubs
├── worker/
│   ├── __init__.py
│   └── worker.py               # gRPC Inference Worker (port 50051)
├── gateway/
│   ├── __init__.py
│   └── app.py                  # FastAPI Ingress Gateway (port 8000)
├── frontend/
│   ├── index.html              # Dashboard UI
│   └── app.js                  # Frontend client logic
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

---

## 5. Installation

Create virtual environment and install dependencies:

```bash
cd ml-gateway
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 6. Running the gRPC Worker

In Terminal 1:
```bash
cd ml-gateway
source .venv/bin/activate
python -m worker.worker
```

---

## 7. Running the FastAPI Gateway

In Terminal 2:
```bash
cd ml-gateway
source .venv/bin/activate
uvicorn gateway.app:app --host 0.0.0.0 --port 8000
```

---

## 8. Running the Frontend

In Terminal 3:
```bash
cd ml-gateway
source .venv/bin/activate
python -m http.server 3000 --directory frontend
```

Then open your browser and navigate to:
```text
http://localhost:3000
```

---

## 9. Health Check

Test system component health status:

```bash
curl http://localhost:8000/health
```

Expected Response:
```json
{
  "status": "healthy",
  "components": {
    "api_gateway": "healthy",
    "grpc_worker": "connected"
  }
}
```

---

## 10. Synchronous Inference

Send a synchronous ML inference request:

```bash
curl -X POST http://localhost:8000/predict/sync \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-001","input_tensor":[1,2,3,4],"model_name":"demo-model"}'
```

Expected Response:
```json
{
  "request_id": "req-001",
  "worker_id": "worker-node-alpha",
  "output_tensor": [1.5, 3.0, 4.5, 6.0],
  "execution_time_ms": 0.1,
  "gateway_latency_ms": 5.0,
  "processing_type": "synchronous"
}
```

---

## 11. Conclusion

This 3-component architecture provides a clean, minimal, and fully functional Distributed ML Inference Gateway demonstrating core distributed systems principles.
