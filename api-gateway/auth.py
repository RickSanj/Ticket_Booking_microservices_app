from flask import Blueprint, request, jsonify
import requests

auth_bp = Blueprint('auth', __name__)

AUTH_SERVICE_URL = "http://auth-service:8081"


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/login", json=data)
    return jsonify(res.json()), res.status_code


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    res = requests.post(f"{AUTH_SERVICE_URL}/register", json=data)
    return jsonify(res.json()), res.status_code
