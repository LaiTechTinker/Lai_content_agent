from app.db.database import get_connection


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
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(platform) DO UPDATE SET
            account_id = excluded.account_id,
            account_name = excluded.account_name,
            access_token = excluded.access_token,
            refresh_token = excluded.refresh_token,
            token_expires_at = excluded.token_expires_at,
            updated_at = CURRENT_TIMESTAMP
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
    return bool(state_value)