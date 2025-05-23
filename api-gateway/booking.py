import random
from flask import Blueprint, request, jsonify
import requests
from custom_consul.consul_ import ConsulServiceRegistry

booking_bp = Blueprint('booking', __name__)


def get_booking_URL():
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    service_name = 'booking-service'
    discovered_services = consul.discover_service(service_name)
    print(discovered_services, flush=True)

    if discovered_services:
        node = random.choice(discovered_services)
        address = node['address']
        port = node['port']
        return f"http://{address}:{port}"
    raise Exception(f"{service_name} service not found in Consul")


@booking_bp.route("/", methods=["POST"])
def create_booking():
    data = request.get_json()
    try:
        booking_service_url = get_booking_URL()
        res = requests.post(f"{booking_service_url}/", json=data)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@booking_bp.route("/<user_id>", methods=["GET"])
def get_user_bookings(user_id):
    try:
        booking_service_url = get_booking_URL()
        res = requests.get(f"{booking_service_url}/{user_id}")
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@booking_bp.route("/<booking_id>", methods=["PUT"])
def update_booking(booking_id):
    data = request.get_json()
    try:
        booking_service_url = get_booking_URL()
        res = requests.put(f"{booking_service_url}/{booking_id}", json=data)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@booking_bp.route("/available_seats/<event_id>", methods=["GET"])
def get_available_seats(event_id):
    booking_service_url = get_booking_URL()
    res = requests.get(f"{booking_service_url}/available_seats/{event_id}")
    return jsonify(res.json()), res.status_code


@booking_bp.route("/book", methods=["POST"])
def book_seat():
    data = request.get_json()
    booking_service_url = get_booking_URL()
    res = requests.post(f"{booking_service_url}/book", json=data)
    return jsonify(res.json()), res.status_code


@booking_bp.route("/confirm", methods=["POST"])
def confirm_booking():
    data = request.get_json()
    booking_service_url = get_booking_URL()
    res = requests.post(f"{booking_service_url}/confirm", json=data)
    return jsonify(res.json()), res.status_code


@booking_bp.route("/create_seats", methods=["POST"])
def create_seats():
    data = request.get_json()
    try:
        booking_service_url = get_booking_URL()
        res = requests.post(f"{booking_service_url}/create_seats", json=data)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to create seats: {str(e)}"}), 500


@booking_bp.route("/delete_seats/<event_id>", methods=["DELETE"])
def delete_seats(event_id):
    try:
        booking_service_url = get_booking_URL()
        res = requests.delete(f"{booking_service_url}/delete_seats/{event_id}")
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to delete seats: {str(e)}"}), 500
