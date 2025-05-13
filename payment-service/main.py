from flask import Flask, jsonify, request
from confluent_kafka import Consumer
import threading
import uuid
from datetime import datetime
import json
from custom_consul.consul_ import ConsulServiceRegistry
import socket

app = Flask(__name__)

# Simulated in-memory database
payments = {}

KAFKA_TOPIC = "payment_requests"
KAFKA_CONF = {
    'bootstrap.servers': 'localhost:9092',
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

@app.route('/payments/<payment_id>', methods=['GET'])
def get_payment(payment_id):
    payment = payments.get(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    return jsonify(payment), 200

@app.route('/payments', methods=['POST'])
def create_payment():
    data = request.get_json()
    handle_payment(data)
    return jsonify({"status": "created"}), 201

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
    payments[payment_id] = payment
    print(f"[Kafka] Processed payment: {payment_id}")

def kafka_consumer():
    """Background Kafka consumer."""
    consumer = Consumer(KAFKA_CONF)
    consumer.subscribe([KAFKA_TOPIC])

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[Kafka Error] {msg.error()}")
                continue

            try:
                data = json.loads(msg.value().decode('utf-8'))
                if 'amount' in data and 'currency' in data:
                    handle_payment(data)
                else:
                    print("[Kafka] Invalid payment data.")
            except json.JSONDecodeError:
                print("[Kafka] Failed to decode JSON.")
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()



if __name__ == '__main__':
    PORT = 5005
    consul = register_service_consul(PORT)
    threading.Thread(target=kafka_consumer, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, debug=True)
