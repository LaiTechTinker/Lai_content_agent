from datetime import datetime, timezone
import sqlite3

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    normalize_email,
    refresh_expiry,
    verify_password,
)
from app.db.database import get_connection


def _safe_user(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def register_user(name: str, email: str, password: str) -> dict:
    normalized_email = normalize_email(email)
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO users (email, password_hash, name, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (normalized_email, hash_password(password), name.strip() or None),
        )
        connection.commit()
        row = connection.execute(
            "SELECT id, name, email, is_active, created_at, updated_at FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return _safe_user(row)
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("An account with that email already exists.") from exc
    finally:
        connection.close()


def authenticate_user(email: str, password: str) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (normalize_email(email),),
        ).fetchone()
        if not row or not row["is_active"] or not verify_password(password, row["password_hash"]):
            return None
        return dict(row)
    finally:
        connection.close()


def get_user_by_id(user_id: int) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT id, name, email, is_active, created_at, updated_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return _safe_user(row) if row else None
    finally:
        connection.close()


def issue_tokens(user_id: int) -> dict:
    access_token, expires_in = create_access_token(user_id)
    refresh_token = create_refresh_token()
    connection = get_connection()
    try:
        connection.execute(
            "INSERT INTO refresh_sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, hash_refresh_token(refresh_token), refresh_expiry().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


def rotate_refresh_token(refresh_token: str) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT refresh_sessions.*, users.is_active
            FROM refresh_sessions
            JOIN users ON users.id = refresh_sessions.user_id
            WHERE refresh_sessions.token_hash = ?
              AND refresh_sessions.revoked_at IS NULL
            """,
            (hash_refresh_token(refresh_token),),
        ).fetchone()
        if not row or not row["is_active"]:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            return None
        connection.execute(
            "UPDATE refresh_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["id"],),
        )
        connection.commit()
    finally:
        connection.close()
    return issue_tokens(row["user_id"])


def revoke_refresh_token(refresh_token: str) -> bool:
    connection = get_connection()
    try:
        cursor = connection.execute(
            "UPDATE refresh_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE token_hash = ? AND revoked_at IS NULL",
            (hash_refresh_token(refresh_token),),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()