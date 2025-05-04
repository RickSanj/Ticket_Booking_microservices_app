from flask import Flask
from auth import auth_bp
from events import events_bp
from booking import booking_bp
from payment import payment_bp

from consul import ConsulServiceRegistry

app = Flask(__name__)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(events_bp, url_prefix="/events")
app.register_blueprint(booking_bp, url_prefix="/booking")
app.register_blueprint(payment_bp, url_prefix="/payment")


@app.route("/health")
def health():
    return "OK", 200


# -------------------- Entry Point --------------------


def main():
    consul = ConsulServiceRegistry(consul_host='localhost', consul_port=8500)

    service_name = "event-service"
    service_id = "event-service-1"
    service_port = 8082

    try:
        consul.register_service(
            service_name=service_name,
            service_id=service_id,
            port=service_port
        )
        print(f"[Consul] Registered {service_name}")
    except Exception as e:
        print(f"[Consul Error] Failed to register: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
