import random
from flask import Blueprint, request, jsonify, abort, render_template, make_response
import requests
from custom_consul.consul_ import ConsulServiceRegistry

booking_bp = Blueprint('booking', __name__)


def get_service_url(service_name):
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    discovered_services = consul.discover_service(service_name)
    # print(discovered_services, flush=True)

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
        booking_service_url = get_service_url('booking-service')
        res = requests.post(f"{booking_service_url}/", json=data)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# @booking_bp.route("/<user_id>", methods=["GET"])
# def get_user_bookings(user_id):
#     try:
#         booking_service_url = get_service_url('booking-service')
#         res = requests.get(f"{booking_service_url}/{user_id}")
#         return jsonify(res.json()), res.status_code
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@booking_bp.route('/<int:event_id>')
def booking_page(event_id):
    session_id = request.cookies.get("session_id")
    if not session_id:
        abort(401, "Session ID not found in cookies")

    AUTH_SERVICE_URL = get_service_url('auth-service')

    user_id_response = requests.get(f"{AUTH_SERVICE_URL}/get_user_id/{session_id}")

    if user_id_response.status_code != 200:
        abort(user_id_response.status_code, user_id_response.text)

    user_id: int = user_id_response.json().get("user_id")

    response = make_response(render_template('booking.html', event_id=event_id, user_id=user_id))
    response.set_cookie('session_id', session_id, httponly=True, samesite='Lax')

    return response

@booking_bp.route("/available_seats/<event_id>", methods=["GET"])
def get_available_seats(event_id):
    booking_service_url = get_service_url('booking-service')
    res = requests.get(f"{booking_service_url}/available_seats/{event_id}")
    return jsonify(res.json()), res.status_code


@booking_bp.route("/book", methods=["POST"])
def book_seat():
    session_id = request.cookies.get("session_id") # is passed correctly
    if not session_id:
        abort(401, "Session ID not found in cookies")
    cookies = {'session_id': session_id}

    if not session_id:
        abort(401, "No session")
    data = request.get_json()
    booking_service_url = get_service_url('booking-service')

    res = requests.post(f"{booking_service_url}/book", json=data, cookies=cookies)

    return jsonify(res.json()), res.status_code


@booking_bp.route("/confirm", methods=["POST"])
def confirm_booking():
    data = request.get_json()
    booking_service_url = get_service_url('booking-service')
    res = requests.post(f"{booking_service_url}/confirm", json=data)
    return jsonify(res.json()), res.status_code


@booking_bp.route("/create_seats", methods=["POST"])
def create_seats():
    data = request.get_json()
    try:
        booking_service_url = get_service_url('booking-service')
        res = requests.post(f"{booking_service_url}/create_seats", json=data)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to create seats: {str(e)}"}), 500


@booking_bp.route("/delete_seats/<event_id>", methods=["DELETE"])
def delete_seats(event_id):
    try:
        booking_service_url = get_service_url('booking-service')
        res = requests.delete(f"{booking_service_url}/delete_seats/{event_id}")
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to delete seats: {str(e)}"}), 500
