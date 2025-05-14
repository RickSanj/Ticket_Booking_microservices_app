from flask import Flask, jsonify, request
from confluent_kafka import Consumer, KafkaError, KafkaException
import threading
import uuid
from datetime import datetime
import sys
from custom_consul.consul_ import ConsulServiceRegistry
import socket
import json

app = Flask(__name__)

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
        'amount': data.get('amount'),
        'currency': data.get('currency'),
        'status': 'completed',
        'created_at': datetime.utcnow().isoformat()
    }
    print(f"[Kafka] Processed payment: {payment_id}: {payment}", flush=True)

def kafka_consumer():
    """Background Kafka consumer."""
    print("Kafka consumer started")
    consumer = Consumer(KAFKA_CONF)

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
    threading.Thread(target=kafka_consumer, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, debug=True)
