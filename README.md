# Distributed Machine Learning Inference Gateway

A lightweight, high-performance **Distributed ML Inference Gateway** built without Docker for Distributed Systems FA/viva demonstrations.

It demonstrates client-server communication, synchronous gRPC ML inference, asynchronous RabbitMQ message queue processing, WebSocket signaling, and stream-oriented WebRTC media processing in a clean single-page web dashboard.

---

## 🏗️ Architecture Overview

```text
                    FRONTEND DASHBOARD
                      localhost:3000
                            |
                      HTTP / WebSocket
                            |
                            v
                     FASTAPI GATEWAY
                      localhost:8000
                       /          \
                      /            \
                   gRPC          RabbitMQ
                    /                \
                   v                  v
            INFERENCE WORKER     BATCH CONSUMER
              localhost:50051
```

1. **Frontend (`localhost:3000`)**: HTML5 + JS + Tailwind CSS CDN single-page monitoring dashboard with live health indicators, inference forms, activity logs, and real-time webcam streaming.
2. **FastAPI Gateway (`localhost:8000`)**: Ingress API server routing synchronous requests to gRPC worker, publishing batch requests to RabbitMQ queue `batch_inference`, and providing WebSocket signaling endpoints `/ws/signaling`.
3. **gRPC Inference Worker (`localhost:50051`)**: Python gRPC server implementing `InferenceServiceServicer` (`Predict` and `StreamPredict`) with NumPy matrix transformations.
4. **RabbitMQ Batch Consumer**: Consumes durable messages from queue `batch_inference` on `localhost:5672` for asynchronous ML processing.

---

## 📋 Prerequisites & Setup on macOS

### 1. Requirements
* macOS with Homebrew installed
* Python 3.10+ (e.g. `/opt/homebrew/bin/python3.12` or system Python 3)
* RabbitMQ message broker (`brew install rabbitmq`)

### 2. Install RabbitMQ Broker
Start the local RabbitMQ service via Homebrew:
```bash
brew install rabbitmq
brew services start rabbitmq
```
*(Verify RabbitMQ is listening on port `5672`)*

### 3. Create Python Virtual Environment & Install Dependencies
Open terminal in the `ml-gateway` directory:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Generate Protobuf gRPC Python Files
Generate gRPC stubs from `proto/inference.proto` into `generated/`:
```bash
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./generated \
    --grpc_python_out=./generated \
    ./proto/inference.proto
```

---

## 🚀 Running the Distributed System

Launch each component in a separate terminal window from the `ml-gateway` root directory:

### Terminal 1: gRPC Inference Worker
```bash
source venv/bin/activate
python -m worker.worker
```
*(Listens on gRPC port `50051`)*

### Terminal 2: RabbitMQ Batch Consumer
```bash
source venv/bin/activate
python -m worker.batch_consumer
```
*(Consumes messages from RabbitMQ queue `batch_inference`)*

### Terminal 3: FastAPI Gateway
```bash
source venv/bin/activate
python -m uvicorn gateway.app:app --host 0.0.0.0 --port 8000 --reload
```
*(Listens on HTTP/REST port `8000`)*

### Terminal 4: Frontend Web Dashboard
```bash
python3 -m http.server 3000 --directory frontend
```
*(Serves static UI on `http://localhost:3000`)*

---

## 🧪 Demonstration & Viva Guide

Open **`http://localhost:3000`** in your browser.

1. **System Health Panel**: Check that Gateway, gRPC Worker, RabbitMQ, and Batch Consumer all display green **CONNECTED/ONLINE** badges.
2. **Synchronous Inference (gRPC)**: Click **Run Synchronous Inference**. Observe low-latency response, worker ID, execution time, and NumPy transformed output tensor (`[1, 2, 3, 4, 5]` ➔ `[1.5, 3.0, 4.5, 6.0, 7.5]`).
3. **Asynchronous Batch Inference (RabbitMQ)**: Click **Enqueue Batch Job**. Observe immediate non-blocking return with status `ENQUEUED`, and watch Terminal 2 (Batch Consumer) consume and log the processed tensor out-of-band.
4. **Live Webcam & WebSocket Stream**: Click **Start Camera** to request browser `getUserMedia()` WebRTC stream, view video resolution & live FPS. Click **Connect WebSocket** to establish `/ws/signaling` connection and exchange SDP offer frames.
5. **Performance Metrics**: View total request counts and average synchronous latency via `GET /stats`.

---

## 📁 Project Structure

```text
ml-gateway/
├── proto/
│   └── inference.proto
├── gateway/
│   ├── __init__.py
│   └── app.py
├── worker/
│   ├── __init__.py
│   ├── worker.py
│   └── batch_consumer.py
├── generated/
│   ├── __init__.py
│   ├── inference_pb2.py
│   └── inference_pb2_grpc.py
├── frontend/
│   ├── index.html
│   └── app.js
├── requirements.txt
└── README.md
```
