from app.db.database import get_connection


def get_social_account(
    platform: str,
):

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
        raise ValueError(
            f"{platform} account is not connected."
        )

    return {
        "platform": row[0],
        "account_id": row[1],
        "account_name": row[2],
        "access_token": row[3],
        "refresh_token": row[4],
        "token_expires_at": row[5],
    }