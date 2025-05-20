from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from custom_consul.consul_ import ConsulServiceRegistry
import argparse, socket, psycopg2, time, requests, random

# ----- Configuration -----
CONFIG = {
    "DB_NAME": "event_db",
    "DB_USER": "admin",
    "DB_PASSWORD": "pass",
    "DB_HOST": "event-db",
    "DB_PORT": 5432,
    "CONSUL_HOST": "consul-server",
    "CONSUL_PORT": 8500,
    "SERVICE_NAME": "event-service"
}

# ----- Helpers -----

def get_service_url(service_name):
    consul = ConsulServiceRegistry(CONFIG["CONSUL_HOST"], CONFIG["CONSUL_PORT"])
    consul.wait_for_consul()
    services = consul.discover_service(service_name)
    if services:
        node = random.choice(services)
        return f"http://{node['address']}:{node['port']}"
    raise Exception(f"{service_name} not found in Consul")

def wait_for_postgres():
    for i in range(10):
        try:
            psycopg2.connect(
                host=CONFIG["DB_HOST"], port=CONFIG["DB_PORT"],
                user=CONFIG["DB_USER"], password=CONFIG["DB_PASSWORD"],
                dbname=CONFIG["DB_NAME"]
            ).close()
            return
        except psycopg2.OperationalError:
            time.sleep(3)
    raise Exception("PostgreSQL not ready")

def get_db_uri():
    wait_for_postgres()
    return f"postgresql://{CONFIG['DB_USER']}:{CONFIG['DB_PASSWORD']}@{CONFIG['DB_HOST']}:{CONFIG['DB_PORT']}/{CONFIG['DB_NAME']}"

def register_service(port):
    consul = ConsulServiceRegistry(CONFIG["CONSUL_HOST"], CONFIG["CONSUL_PORT"])
    consul.wait_for_consul()
    ip = socket.gethostbyname(socket.gethostname())
    consul.register_service(CONFIG["SERVICE_NAME"], f"{CONFIG['SERVICE_NAME']}-{port}", ip, port)
    return consul

# ----- Flask App Setup -----

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = get_db_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    return app

# ----- Database Model -----

def init_db(app):
    db = SQLAlchemy(app)

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

    return db, Event

# ----- Routes -----

def create_routes(db, Event):
    bp = Blueprint("event", __name__)

    @bp.route("/events", methods=["GET"])
    def get_events():
        return jsonify([e.to_dict() for e in Event.query.all()]), 200

    @bp.route("/events/<int:event_id>", methods=["GET"])
    def get_event(event_id):
        event = db.session.get(Event, event_id)
        return (jsonify(event.to_dict()), 200) if event else (jsonify({"error": "Not found"}), 404)

    @bp.route("/events", methods=["POST"])
    def post_event():
        data = request.get_json()
        event = Event(
            title=data["title"],
            date_time=datetime.fromisoformat(data["date_time"]),
            venue=data["venue"],
            performer=data.get("performer", "")
        )
        db.session.add(event)
        db.session.commit()

        try:
            response = requests.post(
                f"{get_service_url('booking-service')}/create_seats",
                json={"event_id": event.id, "num_seats": data.get("num_seats", 10)},
                timeout=5
            )
            if response.status_code != 200:
                raise Exception("Seat creation failed")
        except Exception:
            db.session.delete(event)
            db.session.commit()
            return jsonify({"error": "Failed to create seats"}), 500

        return jsonify(event.to_dict()), 201

    @bp.route("/events/<int:event_id>", methods=["DELETE"])
    def delete_event(event_id):
        event = db.session.get(Event, event_id)
        if not event:
            return jsonify({"error": "Not found"}), 404

        try:
            response = requests.delete(f"{get_service_url('booking-service')}/delete_seats/{event_id}", timeout=5)
            if response.status_code != 200:
                raise Exception(response.text)
        except Exception as e:
            return jsonify({"error": f"Booking service error: {e}"}), 500

        db.session.delete(event)
        db.session.commit()
        return jsonify({"message": "Event deleted"}), 200

    @bp.route("/health", methods=["GET"])
    def health():
        return "OK", 200

    return bp

# ----- Main Entrypoint -----

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8082)
    port = parser.parse_args().port

    app = create_app()
    consul = register_service(port)

    db, Event = init_db(app)
    app.register_blueprint(create_routes(db, Event))

    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
