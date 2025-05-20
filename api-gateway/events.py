from flask import Blueprint, request, jsonify, abort
import requests
import random
from custom_consul.consul_ import ConsulServiceRegistry

events_bp = Blueprint('events', __name__)

def get_service_url(service_name):
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    discovered_services = consul.discover_service(service_name)
    print(discovered_services, flush=True)

    if discovered_services:
        node = random.choice(discovered_services)
        address = node['address']
        port = node['port']

    else:
        raise Exception(f"{service_name} service not found in Consul")
    return f"http://{address}:{port}"


@events_bp.route("/", methods=["GET"])
def handle_events():
    event_id = request.args.get("event_id")
    EVENT_SERVICE_URL = get_service_url("event-service")

    if event_id:
        print("Fetching single event", flush=True)
        res = requests.get(f"{EVENT_SERVICE_URL}/events/{event_id}")
    else:
        print("Fetching all events", flush=True)
        res = requests.get(f"{EVENT_SERVICE_URL}/events")

    try:
        return jsonify(res.json()), res.status_code
    except ValueError:
        return jsonify({"error": "Invalid response from event-service"}), 500


def get_user_id_from_session(session_id):
    AUTH_SERVICE_URL = get_service_url('auth-service')
    user_id_response = requests.get(f"{AUTH_SERVICE_URL}/get_user_id/{session_id}")
    if user_id_response.status_code != 200:
        abort(user_id_response.status_code, user_id_response.text)
    return user_id_response.json().get("user_id")

# todo only admin (no regular users) can do create_event() or delete_event
@events_bp.route("/", methods=["POST"])
def create_event():
    session_id = request.cookies.get("session_id")

    user_id: int = get_user_id_from_session(session_id)
    AUTH_SERVICE_URL = get_service_url('auth-service')

    is_admin_response = requests.get(f"{AUTH_SERVICE_URL}/is_admin/{user_id}")
    user_admin: bool = is_admin_response.json().get("is_admin")

    if not user_admin:
        abort(403, "Only admin can create events")

    EVENT_SERVICE_URL = get_service_url("event-service")
    data = request.get_json()

    if not data or "title" not in data or "date_time" not in data or "venue" not in data or "performer" not in data:
        return jsonify({"error": "Missing 'title', 'date_time', 'venue', or 'performer'"}), 400

    res = requests.post(f"{EVENT_SERVICE_URL}/events", json=data)

    try:
        return jsonify(res.json()), res.status_code
    except ValueError:
        return jsonify({"error": "Invalid response from event-service"}), 500


@events_bp.route("/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    session_id = request.cookies.get("session_id")

    user_id: int = get_user_id_from_session(session_id)
    AUTH_SERVICE_URL = get_service_url('auth-service')

    is_admin_response = requests.get(f"{AUTH_SERVICE_URL}/is_admin/{user_id}")
    user_admin: bool = is_admin_response.json().get("is_admin")

    if not user_admin:
        abort(403, "Only admin can delete events")

    EVENT_SERVICE_URL = get_service_url("event-service")

    try:
        res = requests.delete(f"{EVENT_SERVICE_URL}/events/{event_id}")
        return jsonify(res.json()), res.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to reach event-service: {str(e)}"}), 500
    except ValueError:
        return jsonify({"error": "Invalid response from event-service"}), 500
