from flask import Blueprint, request, jsonify
import requests

payment_bp = Blueprint('payment', __name__)

PAYMENT_SERVICE_URL = "http://payment-service:8084"


@payment_bp.route("/", methods=["POST"])
def make_payment():
    data = request.get_json()
    res = requests.post(f"{PAYMENT_SERVICE_URL}/", json=data)
    return jsonify(res.json()), res.status_code
