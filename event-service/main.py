from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import os
from datetime import datetime
from custom_consul.consul_ import ConsulServiceRegistry



app = Flask(__name__)
CORS(app)

# PostgreSQL database config
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "events")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "event-db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------- Model --------------------


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(512))
    date = db.Column(db.DateTime, nullable=False)
    venue = db.Column(db.String(256))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "date": self.date.isoformat(),
            "venue": self.venue,
        }

# -------------------- Service --------------------


def create_event(data):
    event = Event(
        title=data["title"],
        description=data.get("description", ""),
        date=datetime.fromisoformat(data["date"]),
        venue=data["venue"],
    )
    db.session.add(event)
    db.session.commit()
    return event


def get_all_events():
    return Event.query.all()


def get_event_by_id(event_id):
    return Event.query.get(event_id)


# -------------------- Routes --------------------
event_bp = Blueprint("event", __name__)


@event_bp.route("/events", methods=["GET"])
def get_events():
    events = get_all_events()
    return jsonify([event.to_dict() for event in events]), 200


@event_bp.route("/events/<int:event_id>", methods=["GET"])
def get_event(event_id):
    event = get_event_by_id(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event.to_dict()), 200


@event_bp.route("/events", methods=["POST"])
def post_event():
    data = request.get_json()
    event = create_event(data)
    return jsonify(event.to_dict()), 201


# -------------------- Register and Health --------------------
app.register_blueprint(event_bp, url_prefix="/")


@app.route("/health")
def health():
    return "OK", 200


# -------------------- Entry Point --------------------

def main():
    consul = ConsulServiceRegistry(consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()
    
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
    app.run(host="0.0.0.0", port=8082)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    main()
