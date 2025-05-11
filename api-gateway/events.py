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
def get_events():
    EVENT_SERVICE_URL = get_event_URL()
    res = requests.get(f"{EVENT_SERVICE_URL}/events")
    return jsonify(res.json()), res.status_code


@events_bp.route("/<event_id>", methods=["GET"])
def get_seats(event_id):
    EVENT_SERVICE_URL = get_event_URL()
    res = requests.get(f"{EVENT_SERVICE_URL}/events/{event_id}")
    return jsonify(res.json()), res.status_code
