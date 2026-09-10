from typing import Literal
from fastapi import APIRouter
from langgraph.types import Command
from pydantic import BaseModel
from app.graphs.content_graph import build_content_graph
router=APIRouter()
config = {
    "configurable": {
        "thread_id": "content-123"
    }
}
class ReviewRequest(BaseModel):
    thread_id: str
    action: Literal["approve", "edit"]
    content: str | None = None

graph=build_content_graph()

@router.post("/reveiw")
def generate_ideas(request:ReviewRequest):
 try:
    result = graph.invoke(
    Command(
        resume={
            "action": request.action,
            "content": request.content,
        }
    ),
    config=config
)
    return result
 except Exception as e:
    return {
       "message":str(e)
    }