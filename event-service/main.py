from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import argparse
from datetime import datetime
from custom_consul.consul_ import ConsulServiceRegistry
import socket
import psycopg2
import time
import requests
import random

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
        return f"http://{address}:{port}"
    raise Exception(f"{service_name} service not found in Consul")

def wait_for_postgres(host, port, user, password, db, retries=10, delay=3):
    for i in range(retries):
        try:
            print(
                f"Attempt {i+1}: Connecting to PostgreSQL at {host}:{port}...", flush=True)
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=db
            )
            conn.close()
            print("✅ PostgreSQL is ready!", flush=True)
            return
        except psycopg2.OperationalError as e:
            print(f"PostgreSQL not ready yet: {e}", flush=True)
            time.sleep(delay)
    raise Exception("❌ PostgreSQL is still not ready after retries.")


def create_app():
    app = Flask(__name__)
    CORS(app)
    return app


def init_db(app):
    db = SQLAlchemy(app)
    return db


def create_event_model(db):
    class Event(db.Model):
        __tablename__ = "events"

        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(128), nullable=False)
        date_time = db.Column(db.DateTime, nullable=False)
        venue = db.Column(db.String(256))
        performer = db.Column(db.String(255))

        def to_dict(self):
            return {
                "id": self.id,
                "title": self.title,
                "date_time": self.date_time.isoformat(),
                "venue": self.venue,
                "performer": self.performer
            }
    return Event


def get_db_URL():
    POSTGRES_DB_NAME = "event_db"
    POSTGRES_USER = "admin"
    POSTGRES_PASSWORD = "pass"
    POSTGRES_HOST = "event-db"
    POSTGRES_PORT = 5432

    wait_for_postgres(
        host="event-db",
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        db=POSTGRES_DB_NAME
    )
    FULL_DB_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB_NAME}"
    return FULL_DB_URI

# Event service functions

def create_event(db, data):
    event = Event(
        title=data["title"],
        date_time=datetime.fromisoformat(data["date_time"]),
        venue=data["venue"],
        performer=data.get("performer", "")
    )
    db.session.add(event)
    db.session.commit()

    # After creating event, call booking service to create seats
    event_id = event.id
    num_seats = data.get("num_seats", 10)

    try:
        response = requests.post(
            f"{get_service_url('booking-service')}/create_seats",
            json={"event_id": event_id, "num_seats": num_seats},
            timeout=5
        )
        if response.status_code != 200:
            db.session.delete(event)
            db.session.commit()
            return jsonify({"error": "Failed to create seats, rolled back event"}), 500
    except Exception as e:
        db.session.delete(event)
        db.session.commit()
        print(f"[Booking Service] Could not reach service: {e}")

    return event


def delete_event(db, event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    try:
        response = requests.delete(
            f"{get_service_url('booking-service')}/delete_seats/{event_id}",
            timeout=5
        )

        if response.status_code != 200:
            return jsonify({"error": f"Failed to delete seats: {response.text}"}), 500
    except Exception as e:
        return jsonify({"error": f"Could not reach Booking Service: {str(e)}"}), 500

    # If seat deletion succeeded, delete the event
    db.session.delete(event)
    db.session.commit()
    return jsonify({"message": f"Event {event_id} and its seats deleted successfully"}), 200

def get_all_events(db):
    return Event.query.all()


def get_event_by_id(db, event_id):
    print("I go here", flush=True)
    return db.session.query(Event).filter(Event.id == event_id).first()


def register_service_consul(port):
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    try:
        consul.register_service(
            service_name="event-service",
            service_id=f"event-service-{port}",
            address=ip_address,
            port=port
        )
        print(f"[Consul] Registered event-service", flush=True)
    except Exception as err:
        print(f"[Consul Error] Failed to register: {err}", flush=True)
    return consul

# Routes


def create_routes(db):
    event_bp = Blueprint("event", __name__)

    @event_bp.route("/events", methods=["GET"])
    def get_events():
        events = get_all_events(db)
        return jsonify([event.to_dict() for event in events]), 200

    @event_bp.route("/events/<int:event_id>", methods=["GET"])
    def get_event(event_id):
        event = get_event_by_id(db, event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404
        return jsonify(event.to_dict()), 200

    @event_bp.route("/events", methods=["POST"])
    def post_event():
        data = request.get_json()
        event = create_event(db, data)
        return jsonify(event.to_dict()), 201

    @event_bp.route("/health")
    def health():
        return "OK", 200

    @event_bp.route("/events/<int:event_id>", methods=["DELETE"])
    def delete_event_by_id(event_id):
        return delete_event(db, event_id)


    return event_bp


# Main entry point for the application

def main():
    parser = argparse.ArgumentParser(
        description="Run event service on a specified port.")
    parser.add_argument('--port', type=int, default=8082,
                        help="Port for the event service")
    port = parser.parse_args().port

    app = create_app()

    consul = register_service_consul(port)

    app.config["SQLALCHEMY_DATABASE_URI"] = get_db_URL()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db = init_db(app)

    global Event
    Event = create_event_model(db)

    app.register_blueprint(create_routes(db))

    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
