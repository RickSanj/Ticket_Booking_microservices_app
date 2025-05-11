from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import argparse
from datetime import datetime
from custom_consul.consul_ import ConsulServiceRegistry
import psycopg2
import time
import socket


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

# Initialize the Flask app and SQLAlchemy


def create_app():
    app = Flask(__name__)
    CORS(app)
    return app

# Initialize the db object


def init_db(app):
    db = SQLAlchemy(app)
    return db

# Define the Event model


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

# Utility function to get DB URL from Consul


def get_db_URL(consul):
    POSTGRES_DB_NAME = "event_db"
    POSTGRES_USER = "admin"
    POSTGRES_PASSWORD = "pass"

    discovered_services = consul.discover_service('event-db')
    print(discovered_services, flush=True)
    if discovered_services:
        POSTGRES_HOST = discovered_services[0]['address']
        POSTGRES_PORT = discovered_services[0]['port']
    else:
        raise Exception("event-db service not found in Consul")

    wait_for_postgres(
        host=POSTGRES_HOST,
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
    return event


def get_all_events(db):
    return Event.query.all()


def get_event_by_id(db, event_id):
    return Event.query.get(event_id)

# Register the service in Consul


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

    # Initialize the database connection
    app.config["SQLALCHEMY_DATABASE_URI"] = get_db_URL(consul)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db = init_db(app)

    # Initialize the event model
    global Event
    Event = create_event_model(db)
    

    app.register_blueprint(create_routes(db))

    # Initialize the database and create all tables
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
