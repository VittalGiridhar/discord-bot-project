import os

from dotenv import load_dotenv
from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

load_dotenv()

SESSION_SECRET = os.environ["SESSION_SECRET"]
ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

COOKIE_NAME = "session"
MAX_AGE = 60 * 60 * 24  # 1 day

serializer = URLSafeTimedSerializer(SESSION_SECRET)


def create_session_cookie(username: str) -> str:
    return serializer.dumps({"username": username})


def get_current_user(request: Request) -> str | None:
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    try:
        data = serializer.loads(cookie, max_age=MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    username = data.get("username")
    return username if username == ADMIN_USERNAME else None
