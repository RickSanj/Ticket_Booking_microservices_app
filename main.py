from flask import Flask, request, redirect, make_response, render_template_string, abort
from passlib.hash import bcrypt
import uuid, json, os

app = Flask(__name__)

### sessions should be redis
### here must be redis init
os.makedirs("sessions", exist_ok=True)


# instead of users we should have data in
# postgres, here should be postgres init
with open("users.json", "r") as f:
    users = json.load(f)

def create_session(user_id: int) -> str:
    session_id = str(uuid.uuid4())
    with open(f"sessions/{session_id}.json", "w") as f:
        json.dump({"user_id": user_id}, f)
    return session_id

def get_session(session_id: str):
    try:
        with open(f"sessions/{session_id}.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def delete_session(session_id: str):
    try:
        os.remove(f"sessions/{session_id}.json")
    except FileNotFoundError:
        pass

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

    if email in users:
        abort(400, "Email already registered")

    hashed_pw = bcrypt.hash(password)
    new_id = max((u.get("user_id", 0) for u in users.values()), default=0) + 1
    users[email] = {
        "hashed_password": hashed_pw,
        "user_id": new_id
    }

    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

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

    user = users.get(email)
    if not user or not bcrypt.verify(password, user["hashed_password"]):
        abort(401, "Invalid credentials")

    session_id = create_session(user["user_id"])
    resp = make_response(redirect("/main"))
    resp.set_cookie("session_id", session_id, httponly=True)
    return resp

@app.route("/main", methods=["GET"])
def main():
    session_id = request.cookies.get("session_id")
    if not session_id:
        abort(401, "No session")

    session = get_session(session_id)
    if not session:
        abort(401, "Invalid or expired session")

    return f"Welcome user #{session['user_id']}!"

@app.route("/logout", methods=["GET"])
def logout():
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id)

    resp = make_response(redirect("/login"))
    resp.delete_cookie("session_id")
    return resp

if __name__ == "__main__":
    app.run(debug=True)
