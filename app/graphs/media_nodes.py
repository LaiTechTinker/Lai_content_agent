from langgraph.types import interrupt

from app.services.audio_service import generate_audio
from app.services.image_service import generate_image
from app.services.media_prompt_service import generate_image_prompt
from app.services.media_service import save_media, update_media
from app.services.generated_content_service import mark_content_completed


MAX_IMAGE_ATTEMPTS = 3
MAX_AUDIO_ATTEMPTS = 3


def image_decision_node(state):
    response = interrupt({
        "type": "image_decision",
        "content_id": state.get("content_id"),
        "question": "Generate an image for this approved post?",
        "options": ["generate", "skip"],
    })
    decision = response.get("action")
    decision = {"generate_image": "generate", "skip_image": "skip"}.get(decision, decision)
    if decision not in {"generate", "skip"}:
        raise ValueError("Image decision must be 'generate' or 'skip'.")

    if decision == "skip":
        media_id = save_media(
            content_id=state["content_id"],
            media_type="image",
            media_url=None,
            status="skipped",
            attempt_count=state.get("image_attempt_count", 0),
        )
        return {
            "image_decision": "skip",
            "image_status": "skipped",
            "image_url": None,
            "image_media_id": media_id,
            "workflow_stage": "audio_decision",
        }

    return {
        "image_decision": "generate",
        "image_status": "generating",
        "image_error": None,
        "workflow_stage": "generating_image",
    }


def generate_image_node(state):
    content = state.get("final_content")
    if not content:
        raise ValueError("Cannot generate image without final content.")

    attempt_count = state.get("image_attempt_count", 0) + 1
    if attempt_count > MAX_IMAGE_ATTEMPTS:
        return {
            "image_status": "failed",
            "image_error": "Maximum image generation attempts reached.",
            "workflow_stage": "image_review",
        }

    try:
        prompt = generate_image_prompt(content=content, platform=state["platform"])
        image_url = generate_image(prompt)
        if not image_url:
            raise RuntimeError("Image provider returned no reference.")
        media_id = save_media(
            content_id=state["content_id"],
            media_type="image",
            media_url=image_url,
            status="generated",
            attempt_count=attempt_count,
        )
        return {
            "image_url": image_url,
            "image_media_id": media_id,
            "image_attempt_count": attempt_count,
            "image_status": "generated",
            "image_error": None,
            "workflow_stage": "image_review",
        }
    except Exception as exc:
        media_id = save_media(
            content_id=state["content_id"],
            media_type="image",
            media_url=None,
            status="failed",
            attempt_count=attempt_count,
            error=str(exc),
        )
        return {
            "image_media_id": media_id,
            "image_attempt_count": attempt_count,
            "image_status": "failed",
            "image_error": str(exc),
            "image_url": None,
            "workflow_stage": "image_review",
        }


def image_review_node(state):
    options = ["regenerate", "skip"]
    if state.get("image_status") == "generated":
        options.insert(0, "accept")
    response = interrupt({
        "type": "image_review",
        "content_id": state.get("content_id"),
        "image_url": state.get("image_url"),
        "status": state.get("image_status"),
        "attempt_count": state.get("image_attempt_count", 0),
        "error": state.get("image_error"),
        "options": options,
    })
    action = response.get("action")
    action = {"accept_image": "accept", "regenerate_image": "regenerate", "skip_image": "skip"}.get(action, action)
    if action not in set(options):
        raise ValueError(f"Image review action must be one of: {', '.join(options)}.")
    if action == "accept":
        update_media(state["image_media_id"], "accepted", state.get("image_url"))
        return {"image_status": "accepted", "workflow_stage": "audio_decision"}
    if action == "skip":
        update_media(state["image_media_id"], "skipped", None)
        return {"image_status": "skipped", "image_url": None, "workflow_stage": "audio_decision"}
    if state.get("image_attempt_count", 0) >= MAX_IMAGE_ATTEMPTS:
        raise ValueError("Maximum image generation attempts reached; choose skip.")
    return {"image_status": "regenerating", "workflow_stage": "generating_image"}


def image_review_router(state):
    if state.get("image_status") == "regenerating":
        return "regenerate"
    return "audio"


def audio_decision_node(state):
    response = interrupt({
        "type": "audio_decision",
        "content_id": state.get("content_id"),
        "question": "Generate audio for this approved post?",
        "options": ["generate", "skip"],
    })
    decision = response.get("action")
    decision = {"generate_audio": "generate", "skip_audio": "skip"}.get(decision, decision)
    if decision not in {"generate", "skip"}:
        raise ValueError("Audio decision must be 'generate' or 'skip'.")

    if decision == "skip":
        media_id = save_media(
            content_id=state["content_id"],
            media_type="audio",
            media_url=None,
            status="skipped",
            attempt_count=state.get("audio_attempt_count", 0),
        )
        return {
            "audio_decision": "skip",
            "audio_status": "skipped",
            "audio_url": None,
            "audio_media_id": media_id,
            "workflow_stage": "completed",
        }

    return {
        "audio_decision": "generate",
        "audio_status": "generating",
        "audio_error": None,
        "workflow_stage": "generating_audio",
    }


def generate_audio_node(state):
    content = state.get("final_content")
    if not content:
        raise ValueError("Cannot generate audio without final content.")

    attempt_count = state.get("audio_attempt_count", 0) + 1
    if attempt_count > MAX_AUDIO_ATTEMPTS:
        return {
            "audio_status": "failed",
            "audio_error": "Maximum audio generation attempts reached.",
            "workflow_stage": "audio_review",
        }

    try:
        audio_url = generate_audio(content)
        if not audio_url:
            raise RuntimeError("Audio provider returned no reference.")
        media_id = save_media(
            content_id=state["content_id"],
            media_type="audio",
            media_url=audio_url,
            status="generated",
            attempt_count=attempt_count,
        )
        return {
            "audio_url": audio_url,
            "audio_media_id": media_id,
            "audio_attempt_count": attempt_count,
            "audio_status": "generated",
            "audio_error": None,
            "workflow_stage": "audio_review",
        }
    except Exception as exc:
        media_id = save_media(
            content_id=state["content_id"],
            media_type="audio",
            media_url=None,
            status="failed",
            attempt_count=attempt_count,
            error=str(exc),
        )
        return {
            "audio_media_id": media_id,
            "audio_attempt_count": attempt_count,
            "audio_status": "failed",
            "audio_error": str(exc),
            "audio_url": None,
            "workflow_stage": "audio_review",
        }


def audio_review_node(state):
    options = ["regenerate", "skip"]
    if state.get("audio_status") == "generated":
        options.insert(0, "accept")
    response = interrupt({
        "type": "audio_review",
        "content_id": state.get("content_id"),
        "audio_url": state.get("audio_url"),
        "status": state.get("audio_status"),
        "attempt_count": state.get("audio_attempt_count", 0),
        "error": state.get("audio_error"),
        "options": options,
    })
    action = response.get("action")
    action = {"accept_audio": "accept", "regenerate_audio": "regenerate", "skip_audio": "skip"}.get(action, action)
    if action not in set(options):
        raise ValueError(f"Audio review action must be one of: {', '.join(options)}.")
    if action == "accept":
        update_media(state["audio_media_id"], "accepted", state.get("audio_url"))
        return {"audio_status": "accepted", "workflow_stage": "completed"}
    if action == "skip":
        update_media(state["audio_media_id"], "skipped", None)
        return {"audio_status": "skipped", "audio_url": None, "workflow_stage": "completed"}
    if state.get("audio_attempt_count", 0) >= MAX_AUDIO_ATTEMPTS:
        raise ValueError("Maximum audio generation attempts reached; choose skip.")
    return {"audio_status": "regenerating", "workflow_stage": "generating_audio"}


def audio_review_router(state):
    if state.get("audio_status") == "regenerating":
        return "regenerate"
    return "finish"


def save_final_content_node(state):
    mark_content_completed(state["content_id"])
    return {"workflow_stage": "completed"}
