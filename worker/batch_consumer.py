import os
import json
import time
import logging
import numpy as np
import pika

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s"
)
logger = logging.getLogger("BatchConsumer")

QUEUE_NAME = "batch_inference"
WORKER_ID = os.getenv("WORKER_ID", "worker-batch-node-01")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))


def process_message(ch, method, properties, body):
    start_time = time.perf_counter()
    try:
        data = json.loads(body.decode('utf-8'))
        request_id = data.get("request_id", "unknown")
        input_tensor = data.get("input_tensor", [])
        model_name = data.get("model_name", "batch-model")

        # Process tensor using NumPy
        arr = np.array(input_tensor, dtype=np.float32)
        coeff = 1.5 if "demo" in model_name.lower() else 2.0
        output_tensor = (arr * coeff).tolist()

        exec_time_ms = round((time.perf_counter() - start_time) * 1000.0, 4)

        logger.info(f"==================================================")
        logger.info(f"[Batch Consumer] Processed Request ID: {request_id}")
        logger.info(f"[Batch Consumer] Worker ID         : {WORKER_ID}")
        logger.info(f"[Batch Consumer] Model Name        : {model_name}")
        logger.info(f"[Batch Consumer] Input Tensor      : {input_tensor}")
        logger.info(f"[Batch Consumer] Output Tensor     : {output_tensor}")
        logger.info(f"[Batch Consumer] Execution Time    : {exec_time_ms} ms")
        logger.info(f"==================================================")

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        # Reject message without requeue if malformed
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    logger.info(f"Starting Batch Consumer connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}...")
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                connection_attempts=3,
                retry_delay=2
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_message)

        logger.info(f"Waiting for messages in durable queue '{QUEUE_NAME}'. To exit press CTRL+C")
        channel.start_consuming()
    except pika.exceptions.AMQPConnectionError as err:
        logger.error(f"RabbitMQ connection failed: {err}")
        logger.error("Please ensure RabbitMQ service is running at localhost:5672 (e.g. `brew services start rabbitmq`).")
    except KeyboardInterrupt:
        logger.info("Stopping Batch Consumer...")


if __name__ == "__main__":
    main()
