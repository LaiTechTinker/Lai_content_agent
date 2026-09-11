from datetime import datetime

from app.db.database import get_connection


def mark_publishing(content_id: int):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE generated_content
        SET publish_status = ?
        WHERE id = ?
        """,
        ("publishing", content_id),
    )

    conn.commit()
    conn.close()


def mark_published(
    content_id: int,
    external_post_id: str | None,
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE generated_content
        SET
            publish_status = ?,
            published_at = ?,
            external_post_id = ?,
            publish_error = NULL
        WHERE id = ?
        """,
        (
            "published",
            datetime.utcnow().isoformat(),
            external_post_id,
            content_id,
        ),
    )

    conn.commit()
    conn.close()


def mark_publish_failed(
    content_id: int,
    error: str,
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE generated_content
        SET
            publish_status = ?,
            publish_error = ?
        WHERE id = ?
        """,
        (
            "failed",
            error,
            content_id,
        ),
    )

    conn.commit()
    conn.close()


def can_publish(content_id: int) -> bool:

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            status,
            publish_status
        FROM generated_content
        WHERE id = ?
        """,
        (content_id,),
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        raise ValueError(
            "Content does not exist."
        )

    status, publish_status = row

    if status != "approved":
        return False

    if publish_status == "published":
        return False

    return True