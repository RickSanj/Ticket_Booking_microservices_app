from flask import Blueprint, request, redirect, render_template_string, make_response, abort, url_for, render_template
import requests
import random
from custom_consul.consul_ import ConsulServiceRegistry

# Define blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# Function to get auth service URL via Consul
def get_event_URL():
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500
    )
    consul.wait_for_consul()

    service_name = 'auth-service'
    discovered_services = consul.discover_service(service_name)
    print(discovered_services, flush=True)

    if not discovered_services:
        raise Exception(f"{service_name} service not found in Consul")

    node = random.choice(discovered_services)
    address = node['address']
    port = node['port']
    return f"http://{address}:{port}"


# GET /auth/register - show registration form
@auth_bp.route("/register", methods=["GET"])
def register_form():
    return render_template_string("""
    <h2>Register</h2>
    <form action="{{ url_for('auth.register') }}" method="post">
      Email: <input type="email" name="email" required><br>
      Password: <input type="password" name="password" required><br>
      <input type="submit" value="Register">
    </form>
    """)


# POST /auth/register - submit registration
@auth_bp.route("/register", methods=["POST"])
def register():
    AUTH_SERVICE_URL = get_event_URL()
    email = request.form["email"]
    password = request.form["password"]

    res = requests.post(f"{AUTH_SERVICE_URL}/register", json={
        "email": email, "password": password
    })

    if res.status_code != 201:
        abort(res.status_code, res.text)

    return redirect(url_for('auth.login_form'))

# GET /auth/login - show login form
@auth_bp.route("/login", methods=["GET"])
def login_form():
    return render_template_string("""
    <h2>Login</h2>
    <form action="{{ url_for('auth.login') }}" method="post">
      Email: <input type="email" name="email" required><br>
      Password: <input type="password" name="password" required><br>
      <input type="submit" value="Login">
    </form>
    """)


# POST /auth/login - submit login
@auth_bp.route("/login", methods=["POST"])
def login():
    AUTH_SERVICE_URL = get_event_URL()
    email = request.form["email"]
    password = request.form["password"]

    res = requests.post(f"{AUTH_SERVICE_URL}/login", json={
        "email": email, "password": password
    })

    if res.status_code != 200:
        abort(res.status_code, res.text)

    session_id = res.json().get("session_id")

    if not session_id:
        abort(500, "Invalid response from auth service")

    resp = make_response(redirect(url_for('auth.main')))
    resp.set_cookie("session_id", session_id, httponly=True)
    return resp


# GET /auth/main - protected main page
@auth_bp.route("/main", methods=["GET"])
def main():
    session_id = request.cookies.get("session_id")
    if not session_id:
        abort(401, "No session")

    AUTH_SERVICE_URL = get_event_URL()

    user_id_response = requests.get(f"{AUTH_SERVICE_URL}/get_user_id/{session_id}")

    if user_id_response.status_code != 200:
        abort(user_id_response.status_code, user_id_response.text)

    user_id: int = user_id_response.json().get("user_id")

    is_admin_response = requests.get(f"{AUTH_SERVICE_URL}/is_admin/{user_id}")
    user_admin: bool = is_admin_response.json().get("is_admin")

    return f"<h2>Welcome user #{user_id} is admin bool {user_admin}!</h2>"


# GET /auth/logout - logout and redirect to login
@auth_bp.route("/logout", methods=["GET"])
def logout():
    session_id = request.cookies.get("session_id")
    AUTH_SERVICE_URL = get_event_URL()

    if session_id:
        requests.delete(f"{AUTH_SERVICE_URL}/delete_session/{session_id}")

    resp = make_response(redirect(url_for('auth.login_form')))
    resp.delete_cookie("session_id")
    return resp
