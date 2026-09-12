from app.db.database import get_connection
from datetime import datetime
import json


def _now():
    return datetime.utcnow().isoformat()


def save_generated_content(
    idea_id: int | None,
    platform: str,
    content_type: str,
    content: str,
    quality_score: int,
    thread_id: str | None = None,
    prompt: str | None = None,
    selected_idea: dict | None = None,
    research_required: bool | None = None,
    research_query: str | None = None,
    research_results: list | None = None,
    evaluation: dict | None = None,
    quality_feedback: str | None = None,
    refinement_count: int = 0,
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
            quality_score,
            thread_id,
            prompt,
            selected_idea,
            research_required,
            research_query,
            research_results,
            evaluation,
            quality_feedback,
            refinement_count,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            idea_id,
            platform,
            content_type,
            content,
            quality_score,
            thread_id,
            prompt,
            json.dumps(selected_idea) if selected_idea is not None else None,
            int(research_required) if research_required is not None else None,
            research_query,
            json.dumps(research_results or []),
            json.dumps(evaluation) if evaluation is not None else None,
            quality_feedback,
            refinement_count,
            _now(),
        ),
    )

    conn.commit()

    content_id = cursor.lastrowid

    conn.close()

    return content_id

def update_content_after_review(
    content_id: int,
    content: str,
    feedback: str | None = None,
):
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE generated_content
        SET
            content = ?,
            status = ?,
            approved_at = ?,
            review_feedback = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            content,
            "approved",
            datetime.utcnow().isoformat(),
            feedback,
            _now(),
            content_id,
        ),
    )

    conn.commit()
    conn.close()


def update_content_after_rejection(
    content_id: int,
    feedback: str,
):
    conn = get_connection()
    conn.execute(
        """
        UPDATE generated_content
        SET status = ?, review_feedback = ?, updated_at = ?
        WHERE id = ?
        """,
        ("rejected", feedback, _now(), content_id),
    )
    conn.commit()
    conn.close()


def mark_content_completed(content_id: int):
    conn = get_connection()
    conn.execute(
        """
        UPDATE generated_content
        SET status = ?, updated_at = ?, completed_at = ?
        WHERE id = ? AND status = 'approved'
        """,
        ("completed", _now(), _now(), content_id),
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
            created_at,
            updated_at,
            completed_at,
            thread_id,
            prompt,
            selected_idea,
            research_required,
            research_query,
            research_results,
            evaluation,
            quality_feedback,
            refinement_count,
            review_feedback
        FROM generated_content
        WHERE id = ?
        """,
        (content_id,),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    content = dict(row)
    return _decode_content(content)


def _decode_json(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _decode_content(content: dict) -> dict:
    content["final_content"] = content["content"]
    content["selected_idea"] = _decode_json(content.get("selected_idea"), None)
    content["research_results"] = _decode_json(content.get("research_results"), [])
    content["evaluation"] = _decode_json(content.get("evaluation"), None)
    content["research_used"] = bool(content.get("research_required"))
    return content


def list_content(
    page: int = 1,
    limit: int = 20,
    platform: str | None = None,
    content_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    date: str | None = None,
):
    conditions = []
    parameters = []
    if platform:
        conditions.append("platform = ?")
        parameters.append(platform)
    if content_type:
        conditions.append("content_type = ?")
        parameters.append(content_type)
    if status:
        conditions.append("status = ?")
        parameters.append(status)
    if date:
        conditions.append("date(created_at) = date(?)")
        parameters.append(date)
    if search:
        conditions.append("(content LIKE ? OR prompt LIKE ? OR selected_idea LIKE ?)")
        pattern = f"%{search}%"
        parameters.extend([pattern, pattern, pattern])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * limit
    conn = get_connection()
    total = conn.execute(
        f"SELECT COUNT(*) FROM generated_content {where}", parameters
    ).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT id, idea_id, platform, content_type, content, quality_score,
               status, created_at, updated_at, completed_at, approved_at,
               thread_id, prompt, selected_idea, research_required,
               research_query, research_results, evaluation, quality_feedback,
               refinement_count, review_feedback
        FROM generated_content
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        [*parameters, limit, offset],
    ).fetchall()
    conn.close()
    return [_decode_content(dict(row)) for row in rows], total


def delete_content(content_id: int) -> bool:
    conn = get_connection()
    publication = conn.execute(
        "SELECT 1 FROM content_publications WHERE content_id = ? LIMIT 1",
        (content_id,),
    ).fetchone()
    if publication:
        conn.close()
        raise ValueError("Content with publication history cannot be deleted.")
    conn.execute("DELETE FROM content_media WHERE content_id = ?", (content_id,))
    cursor = conn.execute("DELETE FROM generated_content WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def update_content_metadata(
    content_id: int,
    final_content: str | None = None,
    platform: str | None = None,
    content_type: str | None = None,
    status: str | None = None,
) -> dict | None:
    updates = []
    values = []
    if final_content is not None:
        updates.append("content = ?")
        values.append(final_content)
    if platform is not None:
        updates.append("platform = ?")
        values.append(platform)
    if content_type is not None:
        updates.append("content_type = ?")
        values.append(content_type)
    if status is not None:
        if status not in {"draft", "approved", "rejected", "completed"}:
            raise ValueError("Invalid content status.")
        updates.append("status = ?")
        values.append(status)
    if not updates:
        return get_content(content_id)

    updates.append("updated_at = ?")
    values.extend([_now(), content_id])
    conn = get_connection()
    cursor = conn.execute(
        f"UPDATE generated_content SET {', '.join(updates)} WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        return None
    return get_content(content_id)