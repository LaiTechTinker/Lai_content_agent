from app.db.database import get_connection
from datetime import datetime


def save_generated_content(
    idea_id: int | None,
    platform: str,
    content_type: str,
    content: str,
    quality_score: int,
):
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO generated_content
        (
            idea_id,
            platform,
            content_type,
            content,
            quality_score
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            idea_id,
            platform,
            content_type,
            content,
            quality_score,
        ),
    )

    conn.commit()

    content_id = cursor.lastrowid

    conn.close()

    return content_id

def update_content_after_review(
    content_id: int,
    content: str,
):
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE generated_content
        SET
            content = ?,
            status = ?,
            approved_at = ?
        WHERE id = ?
        """,
        (
            content,
            "approved",
            datetime.utcnow().isoformat(),
            content_id,
        ),
    )

    conn.commit()
    conn.close()




def get_content(content_id: int):
    connection=get_connection()

    row = connection.execute(
        """
        SELECT
            id,
            idea_id,
            platform,
            content_type,
            content,
            quality_score,
            status,
            approved_at,
            published_at,
            publish_status,
            external_post_id,
            publish_error,
            created_at
        FROM generated_content
        WHERE id = ?
        """,
        (content_id,),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)