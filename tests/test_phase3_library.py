from pathlib import Path

from app.db.database import get_connection
from app.services import generated_content_service as content_service
from app.services import media_service


def _use_temp_db(monkeypatch, tmp_path):
    db_path = str(Path(tmp_path) / "content.db")
    monkeypatch.setattr(
        content_service,
        "get_connection",
        lambda: get_connection(db_path),
    )
    monkeypatch.setattr(
        media_service,
        "get_connection",
        lambda: get_connection(db_path),
    )
    return db_path


def test_library_record_contains_canonical_content_and_metadata(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    content_id = content_service.save_generated_content(
        idea_id=2,
        platform="LinkedIn",
        content_type="technical",
        content="AI edited final content",
        quality_score=9,
        thread_id="thread-1",
        prompt="Write about RAG",
        selected_idea={"title": "RAG title"},
        research_required=True,
        research_query="latest RAG systems",
        research_results=[{"title": "source"}],
        evaluation={"score": 9, "should_refine": False},
        quality_feedback="strong",
        refinement_count=1,
    )
    content_service.update_content_after_review(
        content_id,
        "Human approved edited content",
        "Looks authentic",
    )

    record = content_service.get_content(content_id)

    assert record["final_content"] == "Human approved edited content"
    assert record["prompt"] == "Write about RAG"
    assert record["selected_idea"]["title"] == "RAG title"
    assert record["research_used"] is True
    assert record["evaluation"]["score"] == 9
    assert record["review_feedback"] == "Looks authentic"
    assert record["thread_id"] == "thread-1"


def test_library_filters_paginates_and_searches(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    for index in range(3):
        content_service.save_generated_content(
            idea_id=None,
            platform="X" if index < 2 else "LinkedIn",
            content_type="technical",
            content=f"Post about RAG {index}",
            quality_score=8,
            prompt=f"RAG prompt {index}",
        )

    records, total = content_service.list_content(
        page=1,
        limit=1,
        platform="X",
        search="RAG",
    )

    assert total == 2
    assert len(records) == 1
    assert records[0]["final_content"].startswith("Post about RAG")


def test_current_media_prefers_accepted_attempt(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    content_id = content_service.save_generated_content(
        idea_id=None,
        platform="X",
        content_type="technical",
        content="approved",
        quality_score=8,
    )
    media_service.save_media(content_id, "image", "attempt-1.jpg", "failed", 1, "bad")
    media_service.save_media(content_id, "image", "attempt-2.jpg", "generated", 2)
    accepted_id = media_service.save_media(
        content_id,
        "image",
        "attempt-3.jpg",
        "accepted",
        3,
    )

    media = media_service.get_media_for_content(content_id)

    assert media["image"]["id"] == accepted_id
    assert media["image"]["media_url"] == "attempt-3.jpg"
    assert media["audio"] is None


def test_completion_is_separate_from_approval(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    content_id = content_service.save_generated_content(
        idea_id=None,
        platform="X",
        content_type="technical",
        content="approved",
        quality_score=8,
    )
    content_service.update_content_after_review(content_id, "approved", None)
    assert content_service.get_content(content_id)["status"] == "approved"

    content_service.mark_content_completed(content_id)

    assert content_service.get_content(content_id)["status"] == "completed"


def test_metadata_update_and_delete_remove_media_rows(monkeypatch, tmp_path):
    db_path = _use_temp_db(monkeypatch, tmp_path)
    content_id = content_service.save_generated_content(
        idea_id=None,
        platform="X",
        content_type="technical",
        content="old",
        quality_score=8,
    )
    media_service.save_media(content_id, "audio", "audio.wav", "accepted", 1)

    updated = content_service.update_content_metadata(
        content_id,
        final_content="new",
        status="approved",
    )
    assert updated["final_content"] == "new"
    assert updated["status"] == "approved"

    assert content_service.delete_content(content_id) is True
    assert content_service.get_content(content_id) is None
    with get_connection(db_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM content_media WHERE content_id = ?",
            (content_id,),
        ).fetchone()[0] == 0
