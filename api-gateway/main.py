import socket
from flask import Flask
from auth import auth_bp
from events import events_bp
from booking import booking_bp
from payment import payment_bp

from custom_consul.consul_ import ConsulServiceRegistry


app = Flask(__name__)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(events_bp, url_prefix="/events")
app.register_blueprint(booking_bp, url_prefix="/booking")
app.register_blueprint(payment_bp, url_prefix="/payment")


@app.route("/health")
def health():
    return "OK", 200


@app.route("/")
def home():
    return "Welcome to Ticket Booking Service"

# -------------------- Entry Point --------------------


def main():
    consul = ConsulServiceRegistry()
    consul.wait_for_consul()

    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    service_name = "api-gateway"
    service_id = "api-gateway-1"
    service_port = 8080
    print(f"Trying to Register {service_name}", flush=True)
    try:
        consul.register_service(
            service_name=service_name,
            service_id=service_id,
            port=service_port,
            address=ip_address
        )
        print(f"[Consul] Registered {service_name}", flush=True)
    except Exception as err:
        print(f"[Consul Error] Failed to register: {err}", flush=True)

    app.run(host="0.0.0.0", port=service_port)


if __name__ == "__main__":
    main()
