from flask import Flask, jsonify, request
from confluent_kafka import Consumer, KafkaError, KafkaException
import threading
import uuid
from datetime import datetime
import sys
from custom_consul.consul_ import ConsulServiceRegistry
import socket
import json
import random
import requests
import time
import logging

MAX_RETRIES = 10
RETRY_DELAY = 5
app = Flask(__name__)


def get_service_url(service_name):
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    discovered_services = consul.discover_service(service_name)
    if discovered_services:
        node = random.choice(discovered_services)
        address = node['address']
        port = node['port']
        return f"http://{address}:{port}"
    raise Exception(f"{service_name} service not found in Consul")


KAFKA_TOPIC = "payments"
KAFKA_CONF = {
    'bootstrap.servers': 'kafka-payment:19092',
    'group.id': 'payment_service_group',
    'auto.offset.reset': 'earliest'
}

def register_service_consul(port):
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    try:
        consul.register_service(
            service_name="payment-service",
            service_id=f"payment-service-{port}",
            address=ip_address,
            port=port
        )
        print(f"[Consul] Registered event-service", flush=True)
    except Exception as err:
        print(f"[Consul Error] Failed to register: {err}", flush=True)
    return consul


@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

def handle_payment(data):
    """Simulates payment processing and stores it."""
    payment_id = str(uuid.uuid4())
    payment = {
        'id': payment_id,
        'ticket_id': data.get('ticket_id'),
        'user_id': data.get('user_id'),
        'event_id': data.get('event_id'),
        'amount': data.get('amount'),
        'status': 'completed',
        'created_at': datetime.utcnow().isoformat()
    }
    print(f"[Kafka] Processed payment: {payment_id}: {payment}", flush=True)

    booking_data = {"event_id": payment["event_id"], "ticket_id": payment["ticket_id"], "user_id": payment["user_id"]}

    API_SERVICE_URL = get_service_url("api-gateway")

    requests.post(f"{API_SERVICE_URL}/booking/confirm", json=booking_data)




def create_consumer_with_retries(conf, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    attempt = 0
    while attempt < max_retries:
        try:
            consumer = Consumer(conf)
            consumer.list_topics(timeout=5)
            logging.info("Kafka consumer successfully connected.")
            return consumer
        except KafkaException as e:
            attempt += 1
            logging.warning(f"Kafka not ready (attempt {attempt}/{max_retries}): {e}")
            time.sleep(retry_delay)
        except Exception as e:
            attempt += 1
            logging.error(f"Unexpected error when creating Kafka consumer (attempt {attempt}): {e}")
            time.sleep(retry_delay)
    raise RuntimeError("Failed to connect to Kafka after several retries.")

def kafka_consumer():
    """Background Kafka consumer."""
    print("Kafka consumer started")
    consumer = create_consumer_with_retries(KAFKA_CONF)

    try:
        consumer.subscribe([KAFKA_TOPIC])

        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None: continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    sys.stderr.write('%% %s [%d] reached end at offset %d\n' %
                                    (msg.topic(), msg.partition(), msg.offset()))
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                data = json.loads(msg.value().decode('utf-8'))
                handle_payment(data)

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

if __name__ == '__main__':
    PORT = 5050
    consul = register_service_consul(PORT)
    time.sleep(30)
    threading.Thread(target=kafka_consumer, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, debug=True)
