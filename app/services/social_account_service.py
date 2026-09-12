from app.db.database import get_connection
from datetime import datetime, timedelta
import secrets


def save_social_account(platform: str, account_id: str, account_name: str, access_token: str, refresh_token: str | None = None, token_expires_at: str | None = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO social_accounts (
            platform,
            account_id,
            account_name,
            access_token,
            refresh_token,
            token_expires_at,
            updated_at,
            connected_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(platform) DO UPDATE SET
            account_id = excluded.account_id,
            account_name = excluded.account_name,
            access_token = excluded.access_token,
            refresh_token = excluded.refresh_token,
            token_expires_at = excluded.token_expires_at,
            updated_at = CURRENT_TIMESTAMP
            , connected_at = CURRENT_TIMESTAMP
        """,
        (platform, account_id, account_name, access_token, refresh_token, token_expires_at),
    )
    conn.commit()
    conn.close()
    return True


def get_social_account(platform: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            platform,
            account_id,
            account_name,
            access_token,
            refresh_token,
            token_expires_at
        FROM social_accounts
        WHERE platform = ?
        """,
        (platform,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"{platform} account is not connected.")

    return {
        "platform": row[0],
        "account_id": row[1],
        "account_name": row[2],
        "access_token": row[3],
        "refresh_token": row[4],
        "token_expires_at": row[5],
    }


def create_oauth_state(state_value: str):
    return state_value


def consume_oauth_state(state_value: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT state, platform, code_verifier, created_at FROM oauth_states WHERE state = ?",
        (state_value,),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state_value,))
    conn.commit()
    conn.close()
    if not row:
        return None
    created_at = datetime.fromisoformat(row["created_at"])
    if datetime.utcnow() - created_at > timedelta(minutes=10):
        return None
    return dict(row)


def create_oauth_state_record(platform: str, code_verifier: str | None = None):
    state_value = secrets.token_urlsafe(32)
    conn = get_connection()
    conn.execute(
        "INSERT INTO oauth_states (state, platform, code_verifier) VALUES (?, ?, ?)",
        (state_value, platform, code_verifier),
    )
    conn.commit()
    conn.close()
    return state_value


def list_connected_accounts():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT platform, account_id, account_name, connected_at
        FROM social_accounts
        ORDER BY platform
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def disconnect_social_account(platform: str) -> bool:
    conn = get_connection()
    cursor = conn.execute("DELETE FROM social_accounts WHERE platform = ?", (platform,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0