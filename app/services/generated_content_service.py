from app.db.database import get_connection


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