from typing import Literal

from fastapi import APIRouter
from langgraph.types import Command
from pydantic import BaseModel

from app.graphs.content_graph import graph

router = APIRouter()


class ReviewRequest(BaseModel):
    thread_id: str
    action: Literal["approve", "edit"]
    content: str | None = None

@router.post("/reveiw")
def handle_review(request: ReviewRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    try:
        resume_payload = {"action": request.action, "content": request.content}
        if request.action == "edit":
            if not request.content or not request.content.strip():
                return {"message": "Edited content cannot be empty."}
        result = graph.invoke(
            Command(resume=resume_payload),
            config=config,
        )
        return result
    except Exception as e:
        return {"message": str(e)}