from flask import Flask, request, redirect, make_response, render_template_string, abort
from passlib.hash import bcrypt
import uuid
import psycopg2
import redis

app = Flask(__name__)

POSTGRES_DB_NAME = "autorization"
POSTGRES_USER = "admin"
POSTGRES_PASSWORD = "pass"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5430

REDIS_USERNAME = "user"
REDIS_PASSWORD = "pass"
REDIS_HOST = "localhost"
REDIS_PORT = 6380

# Postgres init
postgres_connection = psycopg2.connect(database=POSTGRES_DB_NAME, user=POSTGRES_USER, password=POSTGRES_PASSWORD, host=POSTGRES_HOST, port=POSTGRES_PORT)
cursor_connection = postgres_connection.cursor()

# Redis init
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, username=REDIS_USERNAME, password=REDIS_PASSWORD)

# Postgres Code
def get_user_password(username):
    password_request ="""
    select
        password
    from
        logging_password
    where
        login = %s
    """

    cursor_connection.execute(password_request, (username, ))

    record = cursor_connection.fetchone()

    return record[0]

def get_user_id(username):
    user_id_request ="""
    select
        user_id
    from
        logging_password
    where
        login = %s
    """

    cursor_connection.execute(user_id_request, (username, ))

    record = cursor_connection.fetchone()

    return record[0]

def get_user_ids():
    user_id_request ="""
    select
        user_id
    from
        logging_password
    """

    cursor_connection.execute(user_id_request)

    record = cursor_connection.fetchone()

    return record

def register_user(username, password):
    set_user_request = """INSERT INTO logging_password VALUES (%s, %s, %s);"""

    new_id = max((get_user_ids()), default=0) + 1

    cursor_connection.execute(set_user_request, (username, bcrypt.hash(password), new_id))

    postgres_connection.commit()

def check_user_existance(login):
    password_request ="""
    select
        login
    from
        logging_password
    where
        login = %s
    """

    cursor_connection.execute(password_request, (login, ))

    record = cursor_connection.fetchone()

    return record is not None


# Redis code
def create_userid_session(user_id: int) -> str:
    session_id = str(uuid.uuid4())

    redis_client.set(session_id, user_id)

    return session_id

def get_userid_session(session_id: str):
    if not redis_client.exists(session_id):
        return None

    user_id = redis_client.get(session_id)

    return user_id

def delete_userid_session(session_id: str):
    redis_client.delete(session_id)

@app.route("/register", methods=["GET"])
def register_form():
    return render_template_string("""
    <form action="/register" method="post">
      Email: <input type="email" name="email"><br>
      Password: <input type="password" name="password"><br>
      <input type="submit" value="Register">
    </form>
    """)

@app.route("/register", methods=["POST"])
def register():
    email = request.form.get("email")
    password = request.form.get("password")

    if check_user_existance(email):
        abort(400, "Email already registered")

    register_user(email, password)

    return redirect("/login")

@app.route("/login", methods=["GET"])
def login_form():
    return render_template_string("""
    <form action="/login" method="post">
      Email: <input type="email" name="email"><br>
      Password: <input type="password" name="password"><br>
      <input type="submit" value="Login">
    </form>
    """)

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    if not check_user_existance(email) or not bcrypt.verify(password, get_user_password(email)):
        abort(401, "Invalid credentials")

    session_id = create_userid_session(get_user_id(email))

    resp = make_response(redirect("/main"))
    resp.set_cookie("session_id", session_id, httponly=True)
    return resp

@app.route("/main", methods=["GET"])
def main():
    session_id = request.cookies.get("session_id")
    if not session_id:
        abort(401, "No session")

    session = get_userid_session(session_id)
    if not session:
        abort(401, "Invalid or expired session")

    return f"Welcome user #{session}!"

@app.route("/logout", methods=["GET"])
def logout():
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_userid_session(session_id)

    resp = make_response(redirect("/login"))
    resp.delete_cookie("session_id")
    return resp

if __name__ == "__main__":
    app.run(debug=True)
