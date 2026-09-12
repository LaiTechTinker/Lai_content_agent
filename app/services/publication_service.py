import json
from datetime import datetime

from app.db.database import get_connection


def _now():
    return datetime.utcnow().isoformat()


def create_publication(content_id, platform, account_id, media_ids=None):
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO content_publications
        (content_id, platform, account_id, status, media_ids, updated_at)
        VALUES (?, ?, ?, 'pending', ?, ?)
        """,
        (content_id, platform, account_id, json.dumps(media_ids or []), _now()),
    )
    conn.commit()
    publication_id = cursor.lastrowid
    conn.close()
    return publication_id


def _update(publication_id, **fields):
    fields["updated_at"] = _now()
    values = list(fields.values()) + [publication_id]
    assignments = ", ".join(f"{field} = ?" for field in fields)
    conn = get_connection()
    conn.execute(
        f"UPDATE content_publications SET {assignments} WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()


def mark_publication_publishing(publication_id):
    _update(publication_id, status="publishing")


def mark_publication_published(publication_id, platform_post_id, platform_post_url):
    _update(
        publication_id,
        status="published",
        platform_post_id=platform_post_id,
        platform_post_url=platform_post_url,
        error_message=None,
        published_at=_now(),
    )


def mark_publication_failed(publication_id, error_message):
    _update(publication_id, status="failed", error_message=error_message)


def _decode(publication):
    try:
        publication["media_ids"] = json.loads(publication.get("media_ids") or "[]")
    except json.JSONDecodeError:
        publication["media_ids"] = []
    return publication


def get_publication(publication_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM content_publications WHERE id = ?",
        (publication_id,),
    ).fetchone()
    conn.close()
    return _decode(dict(row)) if row else None


def list_publications(content_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM content_publications
        WHERE content_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (content_id,),
    ).fetchall()
    conn.close()
    return [_decode(dict(row)) for row in rows]


def has_published_attempt(content_id, platform, account_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT id FROM content_publications
        WHERE content_id = ? AND platform = ?
          AND account_id IS ? AND status = 'published'
        ORDER BY id DESC LIMIT 1
        """,
        (content_id, platform, account_id),
    ).fetchone()
    conn.close()
    return row[0] if row else None


# Compatibility helpers retained for older callers. New publishing uses the
# content_publications table and does not mutate generated_content publish fields.
def mark_publishing(content_id):
    conn = get_connection()
    conn.execute("UPDATE generated_content SET publish_status = ? WHERE id = ?", ("publishing", content_id))
    conn.commit()
    conn.close()


def mark_published(content_id, external_post_id):
    conn = get_connection()
    conn.execute(
        "UPDATE generated_content SET publish_status = ?, published_at = ?, external_post_id = ? WHERE id = ?",
        ("published", _now(), external_post_id, content_id),
    )
    conn.commit()
    conn.close()


def mark_publish_failed(content_id, error):
    conn = get_connection()
    conn.execute(
        "UPDATE generated_content SET publish_status = ?, publish_error = ? WHERE id = ?",
        ("failed", error, content_id),
    )
    conn.commit()
    conn.close()


def can_publish(content_id):
    conn = get_connection()
    row = conn.execute("SELECT status FROM generated_content WHERE id = ?", (content_id,)).fetchone()
    conn.close()
    return bool(row and row[0] in {"approved", "completed"})
