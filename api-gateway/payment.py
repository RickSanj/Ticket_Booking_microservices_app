from flask import Flask, jsonify
from confluent_kafka import Consumer, KafkaException
import threading
import uuid
import random
from datetime import datetime
import json
import time

app = Flask(__name__)

#Instad of this must be
#db init
payments = {}

KAFKA_TOPIC = "payment_requests"
KAFKA_CONF = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'payment_service_group',
    'auto.offset.reset': 'earliest'}

@app.route('/health')
def health():
    return "OK", 200

def handle_payment(data):
    """Simulates payment processing and stores it."""
    payment_id = str(uuid.uuid4())
    payment = {
        'id': payment_id,
        'amount': data.get('amount'),
        'currency': data.get('currency'),
        'status': random.choice(['completed']),
        'created_at': datetime.utcnow().isoformat()
    }
    ### Add to db
    payments[payment_id] = payment

    print(f"[Kafka] Processed payment: {payment_id}")

def kafka_consumer():
    """Background thread consuming Kafka messages."""
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

@app.route('/payments/<payment_id>', methods=['GET'])
def get_payment(payment_id):
    payment = payments.get(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    return jsonify(payment)

@app.route('/')
def index():
    return "Kafka-backed Payment Service is running."

if __name__ == '__main__':
    threading.Thread(target=kafka_consumer, daemon=True).start()
    app.run(debug=True)
