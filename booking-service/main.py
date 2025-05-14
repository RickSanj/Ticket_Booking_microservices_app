from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
import argparse
from datetime import datetime
from custom_consul.consul_ import ConsulServiceRegistry
from cassandra.cluster import Cluster
import socket
import psycopg2
import time
import redis

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
        event_id = int(record["event_id"]) | None
        ticket_id = int(record["ticket_id"]) | None
        user_id = int(record["user_id"]) | None
        price = int(record["price"]) | None
        seat_number = record["seat_number"] | None
        booking_time = datetime.fromisoformat(record["booking_time"]) | None

        if table_name == "tickets" and all([event_id, ticket_id, seat_number, price]):
            self.session.execute("""
            INSERT INTO tickets (event_id, ticket_id, seat_number, price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (event_id, ticket_id, seat_number, price))
        if table_name == "bookings" and all([event_id, ticket_id, user_id, booking_time]):
            self.session.execute("""
            INSERT INTO bookings (event_id, ticket_id, user_id, booking_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (event_id, ticket_id, user_id, booking_time))


def connect_to_cassandra():
    consul = ConsulServiceRegistry(
        consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()

    discovered_services = consul.discover_service('cassandra')
    print(discovered_services, flush=True)
    if discovered_services:
        cas_host = discovered_services[0]['address']
        cas_port = discovered_services[0]['port']
    else:
        raise Exception("cassandra not found in Consul")
    return CassandraClient(cas_host, cas_port, KEYSPACE).connect()


def connect_to_redis():
    # consul = ConsulServiceRegistry(
    #     consul_host='consul-server', consul_port=8500)
    # consul.wait_for_consul()

    # discovered_services = consul.discover_service('locked_tickets')
    # print(discovered_services, flush=True)
    # if discovered_services:
    #     redis_host = discovered_services[0]['address']
    #     redis_port = discovered_services[0]['port']
    # else:
    #     raise Exception("locked_tickets not found in Consul")
    # return redis.Redis(
    #     host="redis-ticket-lock", port=6379, decode_responses=True)
    REDIS_CONFIG = {
        "host": "redis_autorization",
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
        print(f"[Consul] Registered event-service", flush=True)
    except Exception as err:
        print(f"[Consul Error] Failed to register: {err}", flush=True)
    return consul


app = Flask(__name__)
CORS(app)
cassandra_client = connect_to_cassandra()
redis_client = connect_to_redis()
TICKET_LOCK_PREFIX = "ticket_lock"
LOCK_TTL_SECONDS = 300  # 5 minutes



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
                "ticket_id": str(row.ticket_id),
                "seat_number": row.seat_number,
                "price": row.price
            })
    return jsonify(available)


@app.route("/book", methods=["POST"])
def book_seat():
    data = request.json
    event_id = data["event_id"]
    ticket_id = data["ticket_id"]
    user_id = data["user_id"]

    redis_key = f"{TICKET_LOCK_PREFIX}:{event_id}:{ticket_id}"
    if redis_client.exists(redis_key):
        return jsonify({"error": "Ticket temporarily locked or already booked"}), 409

    redis_client.set(redis_key, user_id, ex=LOCK_TTL_SECONDS)

    return jsonify({"message": "Seat locked. Proceed to payment", "ticket_id": ticket_id})


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
    parser.add_argument('--port', type=int, default=8081, help="Port for the logging service")
    port = parser.parse_args().port
    register_service_consul(port)

    app.run(host="0.0.0.0", port=port)
