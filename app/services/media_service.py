from app.db.database import get_connection


def save_media(
    content_id: int,
    media_type: str,
    media_url: str | None,
    status: str = "generated",
    attempt_count: int = 0,
    error: str | None = None,
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
            , status
            , attempt_count
            , error
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            content_id,
            media_type,
            media_url,
            status,
            attempt_count,
            error,
        ),
    )

    conn.commit()

    media_id = cursor.lastrowid

    conn.close()

    return media_id


def update_media(
    media_id: int,
    status: str,
    media_url: str | None = None,
    error: str | None = None,
):
    conn = get_connection()
    conn.execute(
        """
        UPDATE content_media
        SET status = ?, media_url = ?, error = ?
        WHERE id = ?
        """,
        (status, media_url, error, media_id),
    )
    conn.commit()
    conn.close()


def get_media_for_content(content_id: int):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, content_id, media_type, media_url, status,
               attempt_count, error, created_at
        FROM content_media
        WHERE content_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (content_id,),
    ).fetchall()
    conn.close()

    media = {"image": None, "audio": None}
    for media_type in media:
        candidates = [row for row in rows if row["media_type"] == media_type]
        if not candidates:
            continue
        accepted = next(
            (row for row in candidates if row["status"] == "accepted"),
            None,
        )
        media[media_type] = dict(accepted or candidates[0])
    return media


def get_media(media_id: int):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT id, content_id, media_type, media_url, status,
               attempt_count, error, created_at
        FROM content_media
        WHERE id = ?
        """,
        (media_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None