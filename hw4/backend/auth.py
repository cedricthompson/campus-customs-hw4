"""Accounts: sign up, log in, log out, and who's logged in.

Passwords are stored only as salted PBKDF2-HMAC-SHA256 hashes in the format
`pbkdf2_sha256$<salt>$<hex hash>`, matching the seeded users. The hash never
leaves this module: no endpoint returns it, and it is never given to the chat agent.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import get_db
from models import CustomerInfo

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128  # Caps the cost of hashing an oversized password.

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Slow down password guessing: after too many failures, block that email for a while.
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60
_failed_logins: dict[str, list[float]] = defaultdict(list)

INVALID_LOGIN = "Invalid email or password."

router = APIRouter(prefix="/api/auth")


# --- Password hashing -------------------------------------------------------


def _pbkdf2(password: str, salt: str) -> str:
    # Salt is used as text, as in the seeded users' hashes.
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)  # New random salt for every account.
    return f"{ALGORITHM}${salt}${_pbkdf2(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    # Re-hash with the stored salt and compare in constant time.
    return hmac.compare_digest(_pbkdf2(password, salt), expected)


# Hashed against when the email doesn't exist, so a wrong email takes as long as a
# wrong password and response time doesn't reveal which accounts exist.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# --- Helpers ----------------------------------------------------------------


def public_user(row: sqlite3.Row) -> dict:
    # Everything the browser may see about a user. Never includes password_hash.
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
    }


def _is_locked_out(email: str) -> bool:
    cutoff = time.time() - LOCKOUT_SECONDS
    _failed_logins[email] = [t for t in _failed_logins[email] if t > cutoff]
    return len(_failed_logins[email]) >= MAX_FAILED_LOGINS


def _check_password_rules(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")


# --- Endpoints --------------------------------------------------------------


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(body: SignupRequest, request: Request) -> dict:
    first = body.first_name.strip()
    last = body.last_name.strip()
    email = body.email.strip().lower()
    if not first or not last or len(first) > 50 or len(last) > 50:
        raise HTTPException(400, "Please enter your first and last name.")
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(400, "Please enter a valid email address.")
    _check_password_rules(body.password)

    with get_db(write=True) as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "An account with that email already exists.")
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()

    request.session.clear()
    request.session["user_id"] = row["id"]
    return public_user(row)


@router.post("/login")
def login(body: LoginRequest, request: Request) -> dict:
    email = body.email.strip().lower()
    if _is_locked_out(email):
        raise HTTPException(429, "Too many failed attempts. Please try again later.")
    if len(body.password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(401, INVALID_LOGIN)

    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(body.password, stored) or row is None:
        _failed_logins[email].append(time.time())
        raise HTTPException(401, INVALID_LOGIN)

    _failed_logins.pop(email, None)
    request.session.clear()
    request.session["user_id"] = row["id"]
    return public_user(row)


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


def current_user(request: Request) -> CustomerInfo | None:
    """The logged-in customer from the signed session cookie, or None for guests."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, first_name, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    return CustomerInfo(id=row["id"], name=row["name"], first_name=row["first_name"], email=row["email"])


@router.get("/me")
def me(request: Request) -> dict | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        # The site calls /me on load; give guests a random chat id now so the chat
        # endpoint can spot duplicate sends from the very first message.
        request.session.setdefault("chat_guest_id", secrets.token_urlsafe(12))
        return None
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(row) if row else None
