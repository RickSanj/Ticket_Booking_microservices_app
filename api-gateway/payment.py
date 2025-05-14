from flask import Flask, Blueprint, request, render_template_string, jsonify
import random
from custom_consul.consul_ import ConsulServiceRegistry
from confluent_kafka import Producer
import json
from datetime import datetime

payment_bp = Blueprint('payment', __name__, url_prefix="payment")

KAFKA_TOPIC = "payments"
KAFKA_CONF = {'bootstrap.servers': 'kafka-payment:19092'}

def get_payment_service_url():
    consul = ConsulServiceRegistry(consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()
    service_name = 'payment-service'
    services = consul.discover_service(service_name)
    if not services:
        raise Exception("Payment service not found in Consul.")
    node = random.choice(services)
    return f"http://{node['address']}:{node['port']}"

@payment_bp.route("/")
def home():
    return render_template_string("""
    <h2>Create a New Payment</h2>
    <form action="/payment/payments" method="post">
        Amount: <input type="text" name="amount" required><br>
        Currency: <input type="text" name="currency" required><br>
        <input type="submit" value="Create Payment">
    </form>
    """)

@payment_bp.route("/payments", methods=["POST"])
def create_payment():
    amount = request.form.get("amount")
    currency = request.form.get("currency")

    produce_payment(amount, currency, random.randint(1, 100))

    return jsonify({
        "amount": amount,
        "currency": currency
    })


def delivery_report(err, msg):
    """Called once for each message to indicate delivery result."""
    if err is not None:
        print(f"[Producer Error] Message delivery failed: {err}")
    else:
        print(f"[Producer] Message delivered to {msg.topic()} [{msg.partition()}]")

def produce_payment(amount, currency, user_id):
    producer = Producer(KAFKA_CONF)

    payment_data = {
        "amount": amount,
        "currency": currency,
        "timestamp": datetime.now().strftime("%m-%d-%Y %H:%M:%S"),
        "userID": user_id
    }

    producer.produce(
        topic=KAFKA_TOPIC,
        value=json.dumps(payment_data),
        callback=delivery_report
    )

    producer.flush()
