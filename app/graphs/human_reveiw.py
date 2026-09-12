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
        "content": state.get("final_content") or state.get("generated_content"),
        "quality_score": state.get("quality_score"),
        "instruction": (
            "Review the generated content. "
            "You can approve it, edit and approve it, or reject it with feedback."
        ),
    }

    response = interrupt(review_request)

    action = response.get("action")

    if action not in {"approve", "edit", "reject"}:
        raise ValueError(
            "Human action must be 'approve', 'edit', or 'reject'."
        )

    if action == "reject":
        return {
            "human_action": "reject",
            "human_feedback": response.get("feedback", "").strip(),
            "approval_status": "rejected",
            "workflow_stage": "rejected",
        }

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
            "workflow_stage": "finalizing_human_review",
        }

    return {
        "human_action": "approve",
        "approval_status": "approved",
        "workflow_stage": "finalizing_human_review",
    }


def review_action_router(state):
    if state.get("human_action") == "reject":
        return "reject"
    return "approve"

def finalize_human_review_node(state):

    if state.get("human_action") == "edit":
        final_content = state["edited_content"]
    else:
        final_content = state["generated_content"]

    return {
        "final_content": final_content,
        "approval_status": "approved",
        "workflow_stage": "finalizing_human_review",
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
        feedback=state.get("human_feedback"),
    )

    return {
        "approval_status": "approved",
        "workflow_stage": "completed",
    }


def save_rejection_node(state):
    content_id = state.get("content_id")
    if not content_id:
        raise ValueError("Missing content ID.")

    from app.services.generated_content_service import update_content_after_rejection

    update_content_after_rejection(
        content_id=content_id,
        feedback=state.get("human_feedback", ""),
    )
    return {
        "approval_status": "rejected",
        "workflow_stage": "rejected",
    }