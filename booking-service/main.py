from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import requests
import argparse
from datetime import datetime
from custom_consul.consul_ import ConsulServiceRegistry
from cassandra.cluster import Cluster
import socket
import time
import redis
import random

KEYSPACE = "bookings_db"

class CassandraClient:
    def __init__(self, host, port, keyspace):
        self.host = host
        self.port = port
        self.keyspace = keyspace
        self.session = None

    def connect(self):
        retries = 10
        for i in range(retries):
            try:
                cluster = Cluster([self.host], port=self.port)
                self.session = cluster.connect(self.keyspace)
                self.session.set_keyspace(self.keyspace)
                print("Connected to Cassandra!")
                return
            except Exception as e:
                print(
                    f"Retrying Cassandra connection ({i+1}/{retries})... {e}")
                time.sleep(5)
        raise Exception(
            "Failed to connect to Cassandra after multiple attempts.")

    def execute(self, query):
        self.session.execute(query)

    def close(self):
        self.session.shutdown()

    def read_from_table(self, query):
        return self.session.execute(query)

    def insert_record(self, table_name, record):
        event_id = int(record.get("event_id")) if "event_id" in record else None
        ticket_id = int(record.get("ticket_id")) if "ticket_id" in record else None
        user_id = int(record.get("user_id")) if "user_id" in record else None
        price = int(record.get("price")) if "price" in record else None
        seat_number = record.get("seat_number")
        booking_time = None
        if "booking_time" in record:
            try:
                booking_time = datetime.fromisoformat(record["booking_time"])
            except Exception:
                pass

        if table_name == "tickets" and all([event_id, ticket_id, seat_number, price]):
            self.session.execute("""
                INSERT INTO tickets (event_id, ticket_id, seat_number, price)
                VALUES (%s, %s, %s, %s)
            """, (event_id, ticket_id, seat_number, price))

        elif table_name == "bookings" and all([event_id, ticket_id, user_id, booking_time]):
            self.session.execute("""
                INSERT INTO bookings (event_id, ticket_id, user_id, booking_time)
                VALUES (%s, %s, %s, %s)
            """, (event_id, ticket_id, user_id, booking_time))

    def select_records(self, table_name, filters):
        if not filters:
            raise ValueError("Filters are required to select records.")
        where_clause = " AND ".join([f"{key} = %s" for key in filters])
        values = tuple(filters.values())

        query = f"SELECT * FROM {table_name} WHERE {where_clause};"
        return self.session.execute(query, values)

    def delete_record(self, table_name, filters):
        if not filters:
            raise ValueError("Filters are required to delete a record.")
        where_clause = " AND ".join([f"{key} = %s" for key in filters])
        values = tuple(filters.values())

        query = f"DELETE FROM {table_name} WHERE {where_clause};"
        self.session.execute(query, values)

def get_service_url(service_name):
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500
    )
    consul.wait_for_consul()

    discovered_services = consul.discover_service(service_name)
    print(discovered_services, flush=True)

    if not discovered_services:
        raise Exception(f"{service_name} service not found in Consul")

    node = random.choice(discovered_services)
    address = node['address']
    port = node['port']
    return f"http://{address}:{port}"

def connect_to_cassandra():
    client = CassandraClient("cassandra_node", 9042, KEYSPACE)
    client.connect()
    return client

def get_user_id_from_session(session_id):
    AUTH_SERVICE_URL = get_service_url('auth-service')
    user_id_response = requests.get(f"{AUTH_SERVICE_URL}/get_user_id/{session_id}")
    if user_id_response.status_code != 200:
        abort(user_id_response.status_code, user_id_response.text)
    return user_id_response.json().get("user_id")

def connect_to_redis():
    REDIS_CONFIG = {
        "host": "redis-ticket-lock",
        "port": 6379,
        "username": "user",
        "password": "pass"
    }
    return redis.Redis(**REDIS_CONFIG, decode_responses=True)

def register_service_consul(port):
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    try:
        consul.register_service(
            service_name="booking-service",
            service_id=f"booking-service-{port}",
            address=ip_address,
            port=port
        )
        print(f"[Consul] Registered booking-service", flush=True)
    except Exception as err:
        print(f"[Consul Error] Failed to register: {err}", flush=True)
    return consul


app = Flask(__name__)
CORS(app)
cassandra_client = connect_to_cassandra()
redis_client = connect_to_redis()
TICKET_LOCK_PREFIX = "ticket_lock"
LOCK_TTL_SECONDS = 300  # 5 minutes


@app.route("/health")
def health():
    return "OK", 200

@app.route("/available_seats/<event_id>", methods=["GET"])
def get_available_seats(event_id):
    locked_keys = redis_client.keys(f"{TICKET_LOCK_PREFIX}:{event_id}:*")
    locked_tickets = set([key.split(":")[-1] for key in locked_keys])

    query = f"SELECT ticket_id, seat_number, price FROM tickets WHERE event_id={event_id}"
    rows = cassandra_client.read_from_table(query)

    available = []
    for row in rows:
        if str(row.ticket_id) not in locked_tickets:
            available.append({
                "ticket_id": int(row.ticket_id),
                "seat_number": str(row.seat_number),
                "price": float(row.price)
            })
    return jsonify(available)


@app.route("/create_seats", methods=["POST"])
def create_seats():
    data = request.json
    event_id = data["event_id"]
    num_seats = data.get("num_seats", 100)

    for i in range(1, num_seats + 1):
        ticket_id = event_id * 1000 + i
        seat_number = f"S{i:03}"
        price = random.choice([100, 120, 150, 200])

        record = {
            "event_id": event_id,
            "ticket_id": ticket_id,
            "price": price,
            "seat_number": seat_number
        }

        try:
            cassandra_client.insert_record("tickets", record)
        except Exception as e:
            return jsonify({"error": f"Failed to insert ticket {ticket_id}: {str(e)}"}), 500

    return jsonify({"message": f"{num_seats} seats created for event {event_id}"}), 200


@app.route("/delete_seats/<int:event_id>", methods=["DELETE"])
def delete_seats(event_id):
    try:
        rows = cassandra_client.select_records(
            "tickets", {"event_id": event_id})
        if not rows:
            return jsonify({"message": f"No seats found for event {event_id}"}), 200

        for row in rows:
            # Access ticket_id as attribute or by index:
            ticket_id = getattr(row, "ticket_id", None) or row[1]
            cassandra_client.delete_record("tickets", {
                "event_id": event_id,
                "ticket_id": ticket_id
            })


        return jsonify({"message": f"Seats for event {event_id} deleted"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete seats: {str(e)}"}), 500


@app.route("/book", methods=["POST"])
def book_seat():
    session_id = request.cookies.get("session_id")

    data = request.json
    event_id = data["event_id"]
    ticket_id = data["ticket_id"]
    user_id: int = get_user_id_from_session(session_id)

    redis_key = f"{TICKET_LOCK_PREFIX}:{event_id}:{ticket_id}"
    if redis_client.exists(redis_key):
        return jsonify({"error": "Ticket temporarily locked or already booked"}), 409

    redis_client.set(redis_key, user_id, ex=LOCK_TTL_SECONDS)

    # payment_url = #TODO redirect user to payment service

    return jsonify({"message": "Seat locked. Proceed to payment", "ticket_id": ticket_id})


# TODO use this function when user successfully paid. Should be called when consumer(booking) received message from MQ send by payment service  (deletes temporary lock from redis and writes permanent booking betails to cassandra)
@app.route("/confirm", methods=["POST"])
def confirm_booking():
    data = request.json
    event_id = data["event_id"]
    ticket_id = data["ticket_id"]
    user_id = data["user_id"]

    redis_key = f"{TICKET_LOCK_PREFIX}:{event_id}:{ticket_id}"
    locked_user_id = redis_client.get(redis_key)

    if locked_user_id != user_id:
        return jsonify({"error": "No active lock or mismatched user"}), 403

    redis_client.delete(redis_key)

    cassandra_client.session.execute("""
        INSERT INTO bookings (event_id, ticket_id, user_id, booking_time)
        VALUES (%s, %s, %s, toTimestamp(now()))
    """, (event_id, ticket_id, user_id))

    return jsonify({"message": "Booking confirmed!"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run logging service on a specified port.")
    parser.add_argument('--port', type=int, default=8081,
                        help="Port for the logging service")
    port = parser.parse_args().port
    register_service_consul(port)

    app.run(host="0.0.0.0", port=port)
