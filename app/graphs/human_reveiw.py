from langgraph.types import interrupt

from app.services.generated_content_service import (
    update_content_after_review,
)

def human_review_node(state):

    review_request = {
        "type": "content_review",
        "content_id": state.get("content_id"),
        "platform": state.get("platform"),
        "content_type": state.get("content_type"),
        "content": state.get("generated_content"),
        "quality_score": state.get("quality_score"),
        "instruction": (
            "Review the generated content. "
            "You can approve it or provide an edited version."
        ),
    }

    response = interrupt(review_request)

    action = response.get("action")

    if action not in {"approve", "edit"}:
        raise ValueError(
            "Human action must be 'approve' or 'edit'."
        )

    if action == "edit":
        edited_content = response.get("content", "").strip()

        if not edited_content:
            raise ValueError(
                "Edited content cannot be empty."
            )

        return {
            "human_action": "edit",
            "edited_content": edited_content,
            "approval_status": "approved",
        }

    return {
        "human_action": "approve",
        "approval_status": "approved",
    }

def finalize_human_review_node(state):

    if state.get("human_action") == "edit":
        final_content = state["edited_content"]
    else:
        final_content = state["generated_content"]

    return {
        "final_content": final_content,
        "approval_status": "approved",
    }



def save_approval_node(state):

    content_id = state.get("content_id")
    final_content = state.get("final_content")

    if not content_id:
        raise ValueError("Missing content ID.")

    if not final_content:
        raise ValueError("Missing final content.")

    update_content_after_review(
        content_id=content_id,
        content=final_content,
    )

    return {
        "approval_status": "approved",
    }