from flask import Blueprint, request, redirect, render_template_string, make_response, abort, url_for

import requests
import random
from custom_consul.consul_ import ConsulServiceRegistry


auth_bp = Blueprint('auth', __name__)

def get_event_URL():
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    service_name = 'auth-service'
    discovered_services = consul.discover_service(service_name)
    print(discovered_services, flush=True)

    if discovered_services:
        node = random.choice(discovered_services)
        address = node['address']
        port = node['port']

    else:
        raise Exception(f"{service_name} service not found in Consul")
    return f"http://{address}:{port}"

@auth_bp.route("/register", methods=["GET"])
def register_form():
    return render_template_string("""
    <form action="/register" method="post">
      Email: <input type="email" name="email"><br>
      Password: <input type="password" name="password"><br>
      <input type="submit" value="Register">
    </form>
    """)

@auth_bp.route("/register", methods=["POST"])
def register():
    AUTH_SERVICE_URL = get_event_URL()
    email = request.form["email"]
    password = request.form["password"]

    res = requests.post(f"{AUTH_SERVICE_URL}/register", json={"email": email, "password": password})

    if res.status_code != 201:
        abort(res.status_code, res.text)

    return redirect(url_for('/auth/login'))


@auth_bp.route("/login", methods=["GET"])
def login_form():
    return render_template_string("""
    <form action="/login" method="post">
      Email: <input type="email" name="email"><br>
      Password: <input type="password" name="password"><br>
      <input type="submit" value="Login">
    </form>
    """)

@auth_bp.route("/login", methods=["POST"])
def login():
    AUTH_SERVICE_URL = get_event_URL()

    email = request.form["email"]
    password = request.form["password"]

    res = requests.post(f"{AUTH_SERVICE_URL}/login", json={"email": email, "password": password})

    if res.status_code != 200:
        abort(res.status_code, res.text)

    session_id = res.json()["session_id"]

    resp = make_response(redirect("/main"))
    resp.set_cookie("session_id", session_id, httponly=True)
    return resp

@auth_bp.route("/main", methods=["GET"])
def main():
    session_id = request.cookies.get("session_id")
    AUTH_SERVICE_URL = get_event_URL()


    if not session_id:
        abort(401, "No session")

    res = requests.get(f"{AUTH_SERVICE_URL}/session/{session_id}")
    if res.status_code != 200:
        abort(res.status_code, res.text)

    user_id = res.json()["user_id"]
    return f"Welcome user #{user_id}!"

@auth_bp.route("/logout", methods=["GET"])
def logout():
    AUTH_SERVICE_URL = get_event_URL()

    session_id = request.cookies.get("session_id")
    if session_id:
        requests.delete(f"{AUTH_SERVICE_URL}/session/{session_id}")

    resp = make_response(redirect("/login"))
    resp.delete_cookie("session_id")
    return resp
