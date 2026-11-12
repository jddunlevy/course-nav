"""Password hashing and the signed-in user (Story 1.5, D-33).

Standard library only. `hashlib.pbkdf2_hmac` is in the stdlib precisely so that
a small application does not take a dependency to store a password correctly,
which is why `requirements.txt` is unchanged by this story (AR1, AC 7).

What is deliberate here:

  * a per-user salt, so two users who choose the same password do not share a
    hash and a precomputed table buys nothing;
  * the iteration count stored per row rather than as a module constant, so it
    can be raised later without invalidating every existing credential;
  * `hmac.compare_digest` rather than `==`, so verification does not leak the
    length of the matching prefix through timing.

What is NOT claimed: this is a course prototype. The demo passwords are in
`seed.py` and the README in the open, on purpose. The mechanism is real; the
accounts are not secret.
"""

import hashlib
import hmac
import os

from flask import g, session

import db

ALGORITHM = "sha256"
ITERATIONS = 240_000
SALT_BYTES = 16


def hash_password(password, salt=None, iterations=ITERATIONS):
    """-> (hash_hex, salt_hex, iterations). A new random salt unless given one."""
    if salt is None:
        salt = os.urandom(SALT_BYTES)
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)
    digest = hashlib.pbkdf2_hmac(ALGORITHM, password.encode("utf-8"), salt, iterations)
    return digest.hex(), salt.hex(), iterations


def verify_password(password, hash_hex, salt_hex, iterations):
    """True when `password` reproduces the stored hash. Constant-time compare."""
    if not (password and hash_hex and salt_hex):
        return False
    try:
        candidate, _, _ = hash_password(password, salt_hex, iterations)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, hash_hex)


def authenticate(conn, username, password):
    """The `app_user` row for these credentials, or None.

    One return value for "no such user" and for "wrong password" on purpose:
    the caller cannot tell them apart and so cannot leak the difference into
    the page (AC 3), and a username that exists is not confirmed to a guesser.
    """
    row = conn.execute(
        "SELECT * FROM app_user WHERE username = ?", ((username or "").strip(),)
    ).fetchone()
    if row is None:
        # Hash anyway. Returning early on an unknown username makes the reply
        # measurably faster than a wrong password and turns the login form into
        # a user-enumeration oracle.
        hash_password(password or "")
        return None
    if not verify_password(password, row["password_hash"], row["password_salt"],
                           row["password_iterations"]):
        return None
    return row


def login(user_row):
    """Establish the session. Stores the id only -- never the password."""
    session.clear()
    session["user_id"] = user_row["user_id"]
    session.permanent = False


def logout():
    session.clear()


def current_user(conn):
    """The signed-in `app_user` row, or None. Cached per request in `g`."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    cached = getattr(g, "_current_user", None)
    if cached is not None and cached["user_id"] == user_id:
        return cached
    row = conn.execute("SELECT * FROM app_user WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        # The row was deleted or the database was reseeded under a live cookie.
        session.clear()
        return None
    g._current_user = row
    return row


def may_view_student(conn, user_row, student_id):
    """May this signed-in user see this student's record? (Story 1.6)

    Exactly two people may: the student, and their advisor of record. D-25 puts
    one advisor on each student, so "my advisee" is the entire authorisation
    rule -- there is no team, no delegation and no department to widen it to.
    """
    if user_row is None:
        return False
    if user_row["role"] == "student":
        return user_row["student_id"] == student_id
    row = conn.execute(
        "SELECT 1 FROM student WHERE student_id = ? AND advisor_id = ?",
        (student_id, user_row["advisor_id"])).fetchone()
    return row is not None


def current_may_view_student(student_id):
    """`may_view_student` for the user of the current request.

    Opens its own connection: the views each open one of their own already, and
    an authorisation check that depends on the caller remembering to pass the
    right connection is one refactor away from being skipped.
    """
    conn = db.connect()
    try:
        return may_view_student(conn, getattr(g, "user", None), student_id)
    finally:
        conn.close()


def may_view_advisor(user_row, advisor_id):
    """May this signed-in user see this advisor's own screens? (Story 1.6)"""
    return (user_row is not None
            and user_row["role"] == "advisor"
            and user_row["advisor_id"] == advisor_id)


def home_endpoint_for(user_row):
    """(endpoint, kwargs) for the view this user's role opens on (AC 2)."""
    if user_row["role"] == "advisor":
        return "advisor_view", {"advisor_id": user_row["advisor_id"]}
    return "student_view", {"student_id": user_row["student_id"]}
