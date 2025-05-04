from flask import Blueprint, request, jsonify
import requests

booking_bp = Blueprint('booking', __name__)

BOOKING_SERVICE_URL = "http://booking-service:8083"


@booking_bp.route("/", methods=["POST"])
def create_booking():
    data = request.get_json()
    res = requests.post(f"{BOOKING_SERVICE_URL}/", json=data)
    return jsonify(res.json()), res.status_code


@booking_bp.route("/<user_id>", methods=["GET"])
def get_user_bookings(user_id):
    res = requests.get(f"{BOOKING_SERVICE_URL}/{user_id}")
    return jsonify(res.json()), res.status_code
