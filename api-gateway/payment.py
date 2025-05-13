from flask import Flask, Blueprint, request, render_template_string, abort
import requests
import random
from custom_consul.consul_ import ConsulServiceRegistry

payment_bp = Blueprint('payment', __name__)

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
    <h2>Payment Lookup</h2>
    <form action="/payments" method="get">
        Payment ID: <input type="text" name="payment_id"><br>
        <input type="submit" value="Get Payment">
    </form>
    """)

@payment_bp.route("/payments", methods=["GET"])
def fetch_payment():
    payment_id = request.args.get("payment_id")
    if not payment_id:
        abort(400, "Payment ID is required.")

    backend_url = get_payment_service_url()
    res = requests.get(f"{backend_url}/payments/{payment_id}")

    if res.status_code == 404:
        return f"<p>Payment not found</p>", 404
    elif res.status_code != 200:
        abort(res.status_code, res.text)

    payment = res.json()
    return render_template_string(f"""
    <h2>Payment Info</h2>
    <ul>
        <li>ID: {payment['id']}</li>
        <li>Amount: {payment['amount']}</li>
        <li>Currency: {payment['currency']}</li>
        <li>Status: {payment['status']}</li>
        <li>Created At: {payment['created_at']}</li>
    </ul>
    <a href="/">Search another</a>
    """)


from flask import Flask, Blueprint, request, render_template_string, abort
import requests
import random
from custom_consul.consul_ import ConsulServiceRegistry

payment_bp = Blueprint('payment', __name__)

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
    <h2>Payment Lookup</h2>
    <form action="/payments" method="get">
        Payment ID: <input type="text" name="payment_id"><br>
        <input type="submit" value="Get Payment">
    </form>
    <h2>Create a New Payment</h2>
    <form action="/payments" method="post">
        Amount: <input type="text" name="amount" required><br>
        Currency: <input type="text" name="currency" required><br>
        <input type="submit" value="Create Payment">
    </form>
    """)

@payment_bp.route("/payments", methods=["GET"])
def fetch_payment():
    payment_id = request.args.get("payment_id")
    if not payment_id:
        abort(400, "Payment ID is required.")

    backend_url = get_payment_service_url()
    res = requests.get(f"{backend_url}/payments/{payment_id}")

    if res.status_code == 404:
        return f"<p>Payment not found</p>", 404
    elif res.status_code != 200:
        abort(res.status_code, res.text)

    payment = res.json()
    return render_template_string(f"""
    <h2>Payment Info</h2>
    <ul>
        <li>ID: {payment['id']}</li>
        <li>Amount: {payment['amount']}</li>
        <li>Currency: {payment['currency']}</li>
        <li>Status: {payment['status']}</li>
        <li>Created At: {payment['created_at']}</li>
    </ul>
    <a href="/">Search another</a>
    """)

@payment_bp.route("/payments", methods=["POST"])
def create_payment():
    amount = request.form.get("amount")
    currency = request.form.get("currency")

    if not amount or not currency:
        abort(400, "Amount and currency are required.")

    backend_url = get_payment_service_url()
    payment_data = {
        "amount": amount,
        "currency": currency
    }
    res = requests.post(f"{backend_url}/payments", json=payment_data)

    if res.status_code == 201:
        return "<p>Payment created successfully!</p>"
    else:
        abort(res.status_code, res.text)
