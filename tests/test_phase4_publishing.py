import pytest
from fastapi import HTTPException

from app.api.publish import PublishRequest, publish, publishing_accounts
from app.api.publish import platform_callback
from app.db.database import get_connection
from app.services import generated_content_service as content_service
from app.services import media_service
from app.services import publication_service
from app.services import social_account_service
from app.services import oauth_service


def _use_temp_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "content.db")
    modules = [
        content_service,
        media_service,
        publication_service,
        social_account_service,
    ]
    for module in modules:
        monkeypatch.setattr(module, "get_connection", lambda path=db_path: get_connection(path))
    return db_path


def _approved_content():
    content_id = content_service.save_generated_content(
        idea_id=None,
        platform="LinkedIn",
        content_type="technical",
        content="AI draft",
        quality_score=9,
        thread_id="thread-publish",
    )
    content_service.update_content_after_review(
        content_id,
        "Human-approved canonical final content",
    )
    content_service.mark_content_completed(content_id)
    return content_id


def _connected_account():
    social_account_service.save_social_account(
        platform="LinkedIn",
        account_id="urn:li:person:1",
        account_name="Test Account",
        access_token="server-only-token",
    )


def test_completed_content_publishes_exact_final_content(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    content_id = _approved_content()
    _connected_account()
    captured = {}

    def fake_publish_content(platform, content, account):
        captured.update(platform=platform, content=content, account=account)
        return {"post_id": "li-post-1"}

    monkeypatch.setattr("app.api.publish.publish_content", fake_publish_content)

    result = publish(content_id, PublishRequest(platform="linkedin"))

    assert result["status"] == "published"
    assert result["platform_post_id"] == "li-post-1"
    assert captured["content"] == "Human-approved canonical final content"
    assert captured["account"]["access_token"] == "server-only-token"


def test_duplicate_publish_is_blocked_without_republish(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    content_id = _approved_content()
    _connected_account()
    monkeypatch.setattr(
        "app.api.publish.publish_content",
        lambda **kwargs: {"post_id": "li-post-1"},
    )
    publish(content_id, PublishRequest(platform="LinkedIn"))

    with pytest.raises(HTTPException) as error:
        publish(content_id, PublishRequest(platform="LinkedIn"))

    assert error.value.status_code == 409


def test_failed_publish_is_persisted_and_content_survives(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    content_id = _approved_content()
    _connected_account()

    def fail_publish(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.api.publish.publish_content", fail_publish)

    with pytest.raises(HTTPException) as error:
        publish(content_id, PublishRequest(platform="LinkedIn"))

    assert error.value.status_code == 502
    attempts = publication_service.list_publications(content_id)
    assert attempts[0]["status"] == "failed"
    assert content_service.get_content(content_id)["final_content"] == "Human-approved canonical final content"


def test_retry_creates_a_new_publication_attempt(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    content_id = _approved_content()
    _connected_account()
    calls = iter([RuntimeError("first failure"), {"post_id": "second-success"}])

    def publish_sequence(**kwargs):
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr("app.api.publish.publish_content", publish_sequence)
    with pytest.raises(HTTPException):
        publish(content_id, PublishRequest(platform="LinkedIn"))

    first = publication_service.list_publications(content_id)[0]
    result = publish(content_id, PublishRequest(platform="LinkedIn", republish=True))
    attempts = publication_service.list_publications(content_id)

    assert result["status"] == "published"
    assert len(attempts) == 2
    assert first["status"] == "failed"


def test_ineligible_content_and_missing_account_fail_cleanly(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    draft_id = content_service.save_generated_content(
        idea_id=None,
        platform="X",
        content_type="technical",
        content="draft",
        quality_score=5,
    )
    with pytest.raises(HTTPException) as draft_error:
        publish(draft_id, PublishRequest(platform="X"))
    assert draft_error.value.status_code == 400

    approved_id = _approved_content()
    with pytest.raises(HTTPException) as account_error:
        publish(approved_id, PublishRequest(platform="LinkedIn"))
    assert account_error.value.status_code == 400


def test_account_status_does_not_expose_tokens(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    _connected_account()

    result = publishing_accounts()

    assert result[0]["connected"] is True
    assert "access_token" not in result[0]
    assert "refresh_token" not in result[0]


def test_oauth_callback_requires_code_and_state():
    with pytest.raises(HTTPException) as error:
        platform_callback("LinkedIn", code=None, state=None)
    assert error.value.status_code == 400


def test_oauth_callback_rejects_invalid_state(monkeypatch):
    monkeypatch.setattr(
        "app.api.publish.complete_callback",
        lambda platform, code, state: (_ for _ in ()).throw(ValueError("Invalid or expired OAuth state.")),
    )
    with pytest.raises(HTTPException) as error:
        platform_callback("LinkedIn", code="code", state="invalid")
    assert error.value.status_code == 400


def test_linkedin_oauth_callback_stores_account(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("LINKEDIN_REDIRECT_URI", "http://localhost/callback")
    state = social_account_service.create_oauth_state_record("LinkedIn")

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    token_response = Response()
    token_response.payload = {"access_token": "server-token", "refresh_token": "refresh"}
    profile_response = Response()
    profile_response.payload = {"sub": "person-1", "name": "Test Person"}
    monkeypatch.setattr(
        oauth_service.requests,
        "post",
        lambda *args, **kwargs: token_response,
    )
    monkeypatch.setattr(
        oauth_service.requests,
        "get",
        lambda *args, **kwargs: profile_response,
    )

    result = oauth_service.complete_callback("LinkedIn", "auth-code", state)
    account = social_account_service.get_social_account("LinkedIn")

    assert result["account_name"] == "Test Person"
    assert account["account_id"] == "person-1"
    assert account["access_token"] == "server-token"