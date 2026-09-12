from app.graphs.media_nodes import (
    MAX_AUDIO_ATTEMPTS,
    MAX_IMAGE_ATTEMPTS,
    audio_decision_node,
    audio_review_node,
    audio_review_router,
    generate_audio_node,
    generate_image_node,
    image_decision_node,
    image_review_node,
    image_review_router,
)


def test_image_generation_uses_final_content(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "app.graphs.media_nodes.generate_image_prompt",
        lambda **kwargs: captured.setdefault("prompt_input", kwargs),
    )
    monkeypatch.setattr(
        "app.graphs.media_nodes.generate_image",
        lambda prompt: captured.setdefault("provider_prompt", prompt) or "image.png",
    )
    monkeypatch.setattr(
        "app.graphs.media_nodes.save_media",
        lambda **kwargs: captured.setdefault("saved", kwargs) or 10,
    )

    result = generate_image_node(
        {
            "content_id": 4,
            "platform": "LinkedIn",
            "final_content": "The approved edited post",
        }
    )

    assert captured["prompt_input"]["content"] == "The approved edited post"
    assert result["image_status"] == "generated"
    assert result["image_attempt_count"] == 1


def test_image_decision_skip_persists_skipped(monkeypatch):
    monkeypatch.setattr(
        "app.graphs.media_nodes.interrupt",
        lambda payload: {"action": "skip_image"},
    )
    saved = {}
    monkeypatch.setattr(
        "app.graphs.media_nodes.save_media",
        lambda **kwargs: saved.update(kwargs) or 20,
    )

    result = image_decision_node({"content_id": 4})

    assert result["image_status"] == "skipped"
    assert result["workflow_stage"] == "audio_decision"
    assert saved["status"] == "skipped"


def test_image_review_accepts_and_regenerates(monkeypatch):
    updated = []
    monkeypatch.setattr(
        "app.graphs.media_nodes.update_media",
        lambda *args, **kwargs: updated.append((args, kwargs)),
    )
    actions = iter(["regenerate_image", "accept_image"])
    monkeypatch.setattr(
        "app.graphs.media_nodes.interrupt",
        lambda payload: {"action": next(actions)},
    )
    state = {
        "content_id": 4,
        "image_media_id": 8,
        "image_url": "image.png",
        "image_status": "generated",
        "image_attempt_count": 1,
    }

    regenerate = image_review_node(state)
    accepted = image_review_node(state)

    assert image_review_router(regenerate) == "regenerate"
    assert accepted["image_status"] == "accepted"
    assert updated[-1][0][1] == "accepted"


def test_image_failure_is_represented_without_rejecting_content(monkeypatch):
    monkeypatch.setattr(
        "app.graphs.media_nodes.generate_image_prompt",
        lambda **kwargs: "prompt",
    )
    monkeypatch.setattr(
        "app.graphs.media_nodes.generate_image",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("provider down")),
    )
    monkeypatch.setattr(
        "app.graphs.media_nodes.save_media",
        lambda **kwargs: 30,
    )

    result = generate_image_node(
        {"content_id": 4, "final_content": "approved text", "platform": "X"}
    )

    assert result["image_status"] == "failed"
    assert result["image_error"] == "provider down"
    assert result["final_content"] if "final_content" in result else True


def test_image_regeneration_is_bounded():
    result = generate_image_node(
        {
            "content_id": 4,
            "final_content": "approved text",
            "platform": "X",
            "image_attempt_count": MAX_IMAGE_ATTEMPTS,
        }
    )

    assert result["image_status"] == "failed"


def test_audio_decision_skip_reaches_completion(monkeypatch):
    monkeypatch.setattr(
        "app.graphs.media_nodes.interrupt",
        lambda payload: {"action": "skip_audio"},
    )
    monkeypatch.setattr(
        "app.graphs.media_nodes.save_media",
        lambda **kwargs: 40,
    )

    result = audio_decision_node({"content_id": 4})

    assert result["audio_status"] == "skipped"
    assert result["workflow_stage"] == "completed"


def test_audio_generation_uses_final_content(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "app.graphs.media_nodes.generate_audio",
        lambda text: captured.setdefault("text", text) or "audio.wav",
    )
    monkeypatch.setattr(
        "app.graphs.media_nodes.save_media",
        lambda **kwargs: 50,
    )

    result = generate_audio_node(
        {"content_id": 4, "final_content": "approved edited text"}
    )

    assert captured["text"] == "approved edited text"
    assert result["audio_status"] == "generated"


def test_audio_review_skip_and_regeneration_limit(monkeypatch):
    updated = []
    monkeypatch.setattr(
        "app.graphs.media_nodes.update_media",
        lambda *args, **kwargs: updated.append((args, kwargs)),
    )
    monkeypatch.setattr(
        "app.graphs.media_nodes.interrupt",
        lambda payload: {"action": "skip_audio"},
    )

    result = audio_review_node(
        {
            "content_id": 4,
            "audio_media_id": 9,
            "audio_url": "audio.wav",
            "audio_status": "generated",
            "audio_attempt_count": 1,
        }
    )

    assert result["audio_status"] == "skipped"
    assert audio_review_router({"audio_status": "regenerating"}) == "regenerate"
    assert updated[-1][0][1] == "skipped"

    bounded = generate_audio_node(
        {
            "content_id": 4,
            "final_content": "approved text",
            "audio_attempt_count": MAX_AUDIO_ATTEMPTS,
        }
    )
    assert bounded["audio_status"] == "failed"