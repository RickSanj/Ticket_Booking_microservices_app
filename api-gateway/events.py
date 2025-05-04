from flask import Blueprint, request, jsonify
import requests

events_bp = Blueprint('events', __name__)

EVENT_SERVICE_URL = "http://event-service:8082"


@events_bp.route("/", methods=["GET"])
def get_events():
    res = requests.get(f"{EVENT_SERVICE_URL}/")
    return jsonify(res.json()), res.status_code


@events_bp.route("/<event_id>/seats", methods=["GET"])
def get_seats(event_id):
    res = requests.get(f"{EVENT_SERVICE_URL}/{event_id}/seats")
    return jsonify(res.json()), res.status_code
