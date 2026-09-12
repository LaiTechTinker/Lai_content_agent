from typing import Literal

from fastapi import APIRouter
from langgraph.types import Command
from pydantic import BaseModel

from app.graphs.content_graph import graph

router = APIRouter()


class ReviewRequest(BaseModel):
    thread_id: str
    action: Literal[
        "select_idea",
        "approve",
        "edit",
        "reject",
        "generate_image",
        "skip_image",
        "accept_image",
        "regenerate_image",
        "generate_audio",
        "skip_audio",
        "accept_audio",
        "regenerate_audio",
    ]
    selected_idea_id: int | None = None
    content: str | None = None
    feedback: str | None = None

def _resume_review(request: ReviewRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    try:
        resume_payload = {
            "action": request.action,
            "selected_idea_id": request.selected_idea_id,
            "content": request.content,
            "feedback": request.feedback,
        }
        if request.action == "select_idea" and request.selected_idea_id is None:
            return {"message": "selected_idea_id is required."}
        if request.action == "edit":
            if not request.content or not request.content.strip():
                return {"message": "Edited content cannot be empty."}
        if request.action == "reject" and request.feedback is None:
            return {"message": "feedback is required when rejecting content."}
        result = graph.invoke(
            Command(resume=resume_payload),
            config=config,
        )
        return result
    except Exception as e:
        return {"message": str(e)}


@router.post("/review")
def handle_review(request: ReviewRequest):
    return _resume_review(request)


@router.post("/reveiw")
def handle_legacy_review(request: ReviewRequest):
    return _resume_review(request)