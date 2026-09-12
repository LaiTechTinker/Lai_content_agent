import os
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.db.database import get_connection, list_knowledge as list_knowledge_documents
from app.graphs.content_graph import graph
from app.services.document_service import ingest_document
from app.services.generated_content_service import (
    delete_content,
    get_content,
    list_content,
    update_content_metadata,
)
from app.services.media_service import get_media, get_media_for_content
from app.services.publication_service import list_publications

router = APIRouter()


class IdeaRequest(BaseModel):
    topic:str
    platform:str
    content_type:str


class ContentPatchRequest(BaseModel):
    final_content: str | None = Field(default=None, min_length=1)
    platform: str | None = None
    content_type: str | None = None
    status: str | None = None


def _thread_id(prefix: str, request: IdeaRequest) -> str:
    return (
        f"{prefix}-{request.topic.lower().replace(' ', '-')}-"
        f"{request.platform.lower()}-{uuid4().hex}"
    )


def _workflow_response(result: dict, thread_id: str) -> dict:
    interrupt = result.get("__interrupt__")
    return {
        "thread_id": thread_id,
        "workflow_stage": result.get("workflow_stage"),
        "requires_input": bool(interrupt),
        "interrupt": interrupt,
        "research_required": result.get("research_required", False),
        "research_results": result.get("research_results", []),
        "ideas": result.get("ideas", []),
        "selected_idea": result.get("selected_idea"),
        "content_id": result.get("content_id"),
        "content": result.get("final_content") or result.get("generated_content"),
        "quality_score": result.get("quality_score"),
        "quality_feedback": result.get("quality_feedback"),
        "refinement_count": result.get("refinement_count"),
        "approval_status": result.get("approval_status"),
        "image_status": result.get("image_status"),
        "image_url": result.get("image_url"),
        "image_attempt_count": result.get("image_attempt_count"),
        "image_error": result.get("image_error"),
        "audio_status": result.get("audio_status"),
        "audio_url": result.get("audio_url"),
        "audio_attempt_count": result.get("audio_attempt_count"),
        "audio_error": result.get("audio_error"),
    }

class  getIdeaResponse(BaseModel):
    id:int
    topic:str
    title:str
    angle:str
    platform:str
    created_at:str
# class  getGeneratedContentResponse(BaseModel):
#     id:int
#     idea_id:int
#     platform:str
#     content_type:str
#     content:str
#     quality_score:int
#     refinement_count:int
#     created_at:str

@router.post("/content/generate")
def generate_content(request: IdeaRequest):
    thread_id = _thread_id("content", request)
    result = graph.invoke(
        {
            "topic": request.topic,
            "original_prompt": request.topic,
            "thread_id": thread_id,
            "platform": request.platform,
            "content_type": request.content_type,
            "ideas": [],
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    response = _workflow_response(result, thread_id)
    response["requires_review"] = response["workflow_stage"] == "waiting_for_human_review"
    return response


@router.post("/ideas")
def generate_ideas(request: IdeaRequest):
    thread_id = _thread_id("ideas", request)
    result = graph.invoke(
        {
            "topic": request.topic,
            "original_prompt": request.topic,
            "thread_id": thread_id,
            "platform": request.platform,
            "content_type": request.content_type,
            "ideas": [],
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    return _workflow_response(result, thread_id)

@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...)
):

    allowed_extensions = {
        ".pdf",
        ".txt",
        ".md",
    }

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    if extension not in allowed_extensions:
        return {
            "error": "Unsupported file type"
        }

    contents = await file.read()

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension,
    ) as temp_file:

        temp_file.write(contents)

        temp_path = temp_file.name

    try:

        result = ingest_document(
            temp_path
        )

        return result

    finally:

        os.remove(temp_path)


@router.get("/knowledge")
def list_knowledge():
    try:
        result = list_knowledge_documents()
        return result
    except Exception as e:
        return {"error": str(e)}


def _library_item(record: dict, include_publications: bool = False) -> dict:
    media = get_media_for_content(record["id"])
    publications = list_publications(record["id"])
    return {
        "id": record["id"],
        "thread_id": record.get("thread_id"),
        "prompt": record.get("prompt"),
        "platform": record["platform"],
        "content_type": record["content_type"],
        "selected_idea": record.get("selected_idea"),
        "final_content": record.get("final_content"),
        "research_used": record.get("research_used", False),
        "research_query": record.get("research_query"),
        "research_results": record.get("research_results", []),
        "evaluation": record.get("evaluation"),
        "quality_score": record.get("quality_score"),
        "quality_feedback": record.get("quality_feedback"),
        "refinement_count": record.get("refinement_count", 0),
        "status": record.get("status"),
        "review_feedback": record.get("review_feedback"),
        "image": media["image"],
        "audio": media["audio"],
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "completed_at": record.get("completed_at"),
        "publications": publications if include_publications else [
            {
                "id": item["id"],
                "platform": item["platform"],
                "status": item["status"],
                "platform_post_url": item.get("platform_post_url"),
                "published_at": item.get("published_at"),
            }
            for item in publications
        ],
    }


@router.get("/content")
def list_content_library(
    page: int = 1,
    limit: int = 20,
    platform: str | None = None,
    content_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    date: str | None = None,
):
    if page < 1 or limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="page must be >= 1 and limit must be 1-100")
    records, total = list_content(
        page=page,
        limit=limit,
        platform=platform,
        content_type=content_type,
        status=status,
        search=search,
        date=date,
    )
    total_pages = (total + limit - 1) // limit if total else 0
    return {
        "items": [_library_item(record) for record in records],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/content/history")
def list_content_history():
    records, total = list_content(page=1, limit=100)
    return {
        "items": [_library_item(record) for record in records],
        "total": total,
    }


@router.get("/content/{content_id}")
def get_generated_content(content_id: int):
    record = get_content(content_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return _library_item(record, include_publications=True)


@router.patch("/content/{content_id}")
def patch_generated_content(content_id: int, request: ContentPatchRequest):
    try:
        record = update_content_metadata(
            content_id=content_id,
            final_content=request.final_content,
            platform=request.platform,
            content_type=request.content_type,
            status=request.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return _library_item(record)


@router.delete("/content/{content_id}")
def remove_generated_content(content_id: int):
    try:
        deleted = delete_content(content_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"deleted": True, "content_id": content_id}


@router.get("/media/{media_id}")
def serve_media(media_id: int):
    media = get_media(media_id)
    if media is None or media["status"] not in {"generated", "accepted"}:
        raise HTTPException(status_code=404, detail="Media not found")

    reference = media.get("media_url")
    if not reference:
        raise HTTPException(status_code=404, detail="Media file not available")

    root = Path.cwd().resolve()
    path = Path(reference)
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    allowed_extensions = {".png", ".jpg", ".jpeg", ".wav"}
    if root not in path.parents or path.suffix.lower() not in allowed_extensions or not path.is_file():
        raise HTTPException(status_code=404, detail="Media file not available")
    return FileResponse(path)

# @router.get("/ideas/{idea_id}")
# async def get_idea(idea_id:int, response_model=getIdeaResponse) ->:
#  try:
#     idea=await get_idea_by_id(idea_id)
#     if idea is None:
#         return {"error":"Idea not found"}
#     return {
#         "id":idea["id"],
#         "topic":idea["topic"],
#         "title":idea["title"],
#         "angle":idea["angle"],
#         "platform":idea["platform"],
#         "created_at":idea["created_at"]
#     }
#  except Exception as e:
#     return {"error":str(e)}