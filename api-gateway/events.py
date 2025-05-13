from flask import Blueprint, request, jsonify
import requests
import random
from custom_consul.consul_ import ConsulServiceRegistry

events_bp = Blueprint('events', __name__)

def get_event_URL():
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    service_name = 'event-service'
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
    EVENT_SERVICE_URL = get_event_URL()

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


@events_bp.route("/", methods=["POST"])
def create_event():
    EVENT_SERVICE_URL = get_event_URL()
    data = request.get_json()

    if not data or "title" not in data or "date_time" not in data or "venue" not in data or "performer" not in data:
        return jsonify({"error": "Missing 'title', 'date_time', 'venue', or 'performer'"}), 400

    res = requests.post(f"{EVENT_SERVICE_URL}/events", json=data)

    try:
        return jsonify(res.json()), res.status_code
    except ValueError:
        return jsonify({"error": "Invalid response from event-service"}), 500
