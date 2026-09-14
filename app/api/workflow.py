from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.db.database import (
    create_workflow_session,
    get_content_version_summary,
    get_workflow_session,
    owns_workflow_session,
    workflow_session_exists,
    update_workflow_session,
)
from app.graphs.content_graph import graph


router = APIRouter(prefix="/workflow", tags=["workflow"])


class WorkflowStartRequest(BaseModel):
    topic: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    thread_id: str | None = Field(default=None, min_length=1)


class WorkflowResumeRequest(BaseModel):
    action: str
    selected_idea_id: int | None = None
    content: str | None = None
    feedback: str | None = None


def _thread_id(request: WorkflowStartRequest, user_id: int) -> str:
    if request.thread_id:
        return request.thread_id
    from uuid import uuid4

    return f"workflow-{user_id}-{uuid4().hex}"


def _interrupt_from_snapshot(snapshot: Any, result: dict | None = None) -> dict | None:
    interrupts = []
    if result:
        interrupts = result.get("__interrupt__") or []
    if not interrupts and snapshot is not None:
        for task in getattr(snapshot, "tasks", ()) or ():
            interrupts.extend(getattr(task, "interrupts", ()) or ())

    if not interrupts:
        return None
    interrupt = interrupts[0]
    value = getattr(interrupt, "value", interrupt)
    if not isinstance(value, dict):
        value = {"type": "workflow_input", "value": value}
    return value


def _state_values(snapshot: Any, result: dict | None = None) -> dict:
    values = getattr(snapshot, "values", None) if snapshot is not None else None
    return dict(values or result or {})


def _normalize_score(evaluation: Any, quality_score: Any) -> Any:
    score = evaluation.get("score") if isinstance(evaluation, dict) else quality_score
    if score is None:
        return None
    try:
        score = int(score)
    except (TypeError, ValueError):
        return None
    return score * 10 if 0 <= score <= 10 else max(0, min(100, score))


def _response(thread_id: str, user_id: int, snapshot: Any, result: dict | None = None) -> dict:
    values = _state_values(snapshot, result)
    interrupt = _interrupt_from_snapshot(snapshot, result)
    current_stage = values.get("workflow_stage") or ("waiting_for_input" if interrupt else "completed")
    status = "waiting_for_input" if interrupt else (
        "rejected" if values.get("approval_status") == "rejected" else
        "completed" if current_stage == "completed" else "running"
    )
    content_id = values.get("content_id")
    versions = get_content_version_summary(content_id, user_id) if content_id else {
        "version_count": 0,
        "latest_version": None,
    }
    evaluation = values.get("evaluation")
    normalized_evaluation = dict(evaluation) if isinstance(evaluation, dict) else evaluation
    if normalized_evaluation is not None:
        normalized_evaluation["score"] = _normalize_score(evaluation, values.get("quality_score"))

    return {
        "threadId": thread_id,
        "status": status,
        "currentStage": current_stage,
        "interrupt": interrupt,
        "ideas": values.get("ideas", []),
        "selectedIdea": values.get("selected_idea"),
        "content": values.get("final_content") or values.get("generated_content"),
        "evaluation": normalized_evaluation,
        "qualityScore": _normalize_score(evaluation, values.get("quality_score")),
        "refinement": {
            "count": values.get("refinement_count", 0),
            **versions,
        },
        "humanReview": {
            "action": values.get("human_action"),
            "feedback": values.get("human_feedback"),
            "approvalStatus": values.get("approval_status"),
        },
        "media": {
            "imageStatus": values.get("image_status"),
            "imageUrl": values.get("image_url"),
            "audioStatus": values.get("audio_status"),
            "audioUrl": values.get("audio_url"),
        },
        "publishing": {
            "contentId": content_id,
        },
    }


def _snapshot(thread_id: str):
    return graph.get_state({"configurable": {"thread_id": thread_id}})


def _invoke(thread_id: str, user_id: int, command: Any) -> dict:
    try:
        result = graph.invoke(command, config={"configurable": {"thread_id": thread_id}})
        snapshot = _snapshot(thread_id)
        response = _response(thread_id, user_id, snapshot, result)
        update_workflow_session(thread_id, user_id, response["status"], response["currentStage"])
        return response
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Workflow execution failed.") from exc


@router.post("", status_code=status.HTTP_200_OK)
def start_workflow(request: WorkflowStartRequest, current_user: dict = Depends(get_current_user)):
    thread_id = _thread_id(request, current_user["id"])
    if request.thread_id and workflow_session_exists(thread_id):
        raise HTTPException(status_code=409, detail="Workflow thread already exists.")
    create_workflow_session(thread_id, current_user["id"])
    return _invoke(
        thread_id,
        current_user["id"],
        {
            "topic": request.topic,
            "original_prompt": request.topic,
            "thread_id": thread_id,
            "platform": request.platform,
            "content_type": request.content_type,
            "ideas": [],
            "user_id": current_user["id"],
        },
    )


@router.get("/{thread_id}")
def get_workflow(thread_id: str, current_user: dict = Depends(get_current_user)):
    if not owns_workflow_session(thread_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Workflow session not found.")
    try:
        return _response(thread_id, current_user["id"], _snapshot(thread_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Workflow state could not be loaded.") from exc


@router.post("/{thread_id}/resume")
def resume_workflow(
    thread_id: str,
    request: WorkflowResumeRequest,
    current_user: dict = Depends(get_current_user),
):
    if not owns_workflow_session(thread_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Workflow session not found.")
    if request.action == "select_idea" and request.selected_idea_id is None:
        raise HTTPException(status_code=422, detail="selected_idea_id is required.")
    if request.action == "edit" and not (request.content or "").strip():
        raise HTTPException(status_code=422, detail="content is required for an edit.")
    if request.action == "reject" and not (request.feedback or "").strip():
        raise HTTPException(status_code=422, detail="feedback is required for rejection.")
    return _invoke(
        thread_id,
        current_user["id"],
        Command(
            resume={
                "action": request.action,
                "selected_idea_id": request.selected_idea_id,
                "content": request.content,
                "feedback": request.feedback,
            }
        ),
    )