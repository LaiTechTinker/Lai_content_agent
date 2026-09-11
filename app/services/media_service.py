from app.db.database import get_connection


def save_media(
    content_id: int,
    media_type: str,
    media_url: str,
):

    if media_type not in {"image", "audio"}:
        raise ValueError("Invalid media type.")

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO content_media
        (
            content_id,
            media_type,
            media_url
        )
        VALUES (?, ?, ?)
        """,
        (
            content_id,
            media_type,
            media_url,
        ),
    )

    conn.commit()

    media_id = cursor.lastrowid

    conn.close()

    return media_id