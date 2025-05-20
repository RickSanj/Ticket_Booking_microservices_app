from flask import Flask, request, jsonify, abort
from passlib.hash import bcrypt
import uuid
import psycopg2
import redis
import socket
from custom_consul.consul_ import ConsulServiceRegistry
import time

app = Flask(__name__)

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


wait_for_postgres(
    host="postgres-authorization",
    port=5432,
    user="admin",
    password="pass",
    db="authorization"
)

POSTGRES_CONFIG = {
    "database": "authorization",
    "user": "admin",
    "password": "pass",
    "host": "postgres-authorization",
    "port": 5432
}

REDIS_CONFIG = {
    "host": "redis-authorization",
    "port": 6379,
    "username": "user",
    "password": "pass"
}

postgres_conn = psycopg2.connect(**POSTGRES_CONFIG)
postgres_cursor = postgres_conn.cursor()
redis_client = redis.Redis(**REDIS_CONFIG, decode_responses=True)


def get_user_password(username):
    postgres_cursor.execute("SELECT password FROM logging_password WHERE login = %s", (username,))
    record = postgres_cursor.fetchone()
    return record[0] if record else None


@app.route("/is_admin/<user_id>", methods=["GET"])
def is_admin(user_id):
    postgres_cursor.execute("SELECT admin FROM logging_password WHERE user_id = %s", (user_id,))
    record = postgres_cursor.fetchone()

    return  jsonify({"is_admin": record[0] if record else False}), 200

def get_user_id(username):
    postgres_cursor.execute("SELECT user_id FROM logging_password WHERE login = %s", (username,))
    record = postgres_cursor.fetchone()
    return record[0] if record else None

def get_user_ids():
    postgres_cursor.execute("SELECT user_id FROM logging_password")
    return [row[0] for row in postgres_cursor.fetchall()]

def register_user(username, password, admin):
    new_id = max(get_user_ids(), default=0) + 1
    hashed_pw = bcrypt.hash(password)
    postgres_cursor.execute("INSERT INTO logging_password VALUES (%s, %s, %s, %s)", (username, hashed_pw, admin, new_id))
    postgres_conn.commit()

def user_exists(username):
    postgres_cursor.execute("SELECT login FROM logging_password WHERE login = %s", (username,))
    return postgres_cursor.fetchone() is not None

def create_session(user_id):
    session_id = str(uuid.uuid4())
    redis_client.set(session_id, user_id)
    return session_id

def get_userid_by_session(session_id):
    return redis_client.get(session_id) if redis_client.exists(session_id) else None

def delete_session(session_id):
    redis_client.delete(session_id)


@app.route("/health")
def health():
    return "OK", 200


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        abort(400, "Email and password required")

    if user_exists(email):
        abort(409, "Email already registered")

    register_user(email, password, False)
    return jsonify({"message": "User registered"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    stored_pw = get_user_password(email)
    if not stored_pw or not bcrypt.verify(password, stored_pw):
        abort(401, "Invalid credentials")

    session_id = create_session(get_user_id(email))
    return jsonify({"session_id": session_id}), 200

@app.route("/get_user_id/<session_id>", methods=["GET"])
def session_info(session_id):
    user_id = get_userid_by_session(session_id)
    if not user_id:
        abort(401, "Invalid or expired session")
    return jsonify({"user_id": user_id}), 200

@app.route("/delete_session/<session_id>", methods=["DELETE"])
def session_delete(session_id):
    delete_session(session_id)
    return jsonify({"message": "Session deleted"}), 200

def register_service_consul(port):
    consul = ConsulServiceRegistry(consul_host='consul-server', consul_port=8500)
    consul.wait_for_consul()
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    try:
        consul.register_service(
            service_name="auth-service",
            service_id=f"auth-service-{port}",
            address=ip_address,
            port=port
        )
        print(f"[Consul] Registered auth-service", flush=True)
    except Exception as err:
        print(f"[Consul Error] {err}", flush=True)
    return consul

if __name__ == "__main__":
    PORT = 6000
    register_service_consul(PORT)
    register_user("admin@admin", "admin", True)

    app.run(host="0.0.0.0", port=PORT, debug=True)
