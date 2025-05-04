from fastapi import FastAPI, Request, Form, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from passlib.hash import bcrypt
import uuid, json, os

app = FastAPI()

os.makedirs("sessions", exist_ok=True)

with open("users.json", "r") as f:
    users = json.load(f)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/register", response_class=HTMLResponse)
def register_form():
    return """
    <form action="/register" method="post">
      Email: <input type="email" name="email"><br>
      Password: <input type="password" name="password"><br>
      <input type="submit" value="Register">
    </form>
    """

@app.post("/register")
def register(email: str = Form(...), password: str = Form(...)):
    if email in users:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_pw = bcrypt.hash(password)

    # Simple ID generator (increment max existing ID)
    new_id = max((u.get("user_id", 0) for u in users.values()), default=0) + 1

    # Save user in memory
    users[email] = {
        "hashed_password": hashed_pw,
        "user_id": new_id
    }

    # Persist to file
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

    # Redirect to login
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return response


@app.get("/login", response_class=HTMLResponse)
def login_form():
    return """
    <form action="/login" method="post">
      Email: <input type="email" name="email"><br>
      Password: <input type="password" name="password"><br>
      <input type="submit" value="Login">
    </form>
    """

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = users.get(email)
    if not user or not bcrypt.verify(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_id = create_session(user["user_id"])

    response = RedirectResponse(url="/main", status_code=status.HTTP_302_FOUND)
    response.set_cookie("session_id", session_id, httponly=True, secure=False)
    return response

@app.get("/main")
def main(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {"message": f"Welcome user #{session['user_id']}!"}

@app.get("/logout")
def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id)

    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session_id")
    return response
