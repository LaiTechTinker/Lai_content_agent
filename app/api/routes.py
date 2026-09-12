import os
import tempfile

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from app.db.database import get_connection, list_knowledge
from app.graphs.content_graph import graph
from app.services.document_service import ingest_document

router = APIRouter()


class IdeaRequest(BaseModel):
    topic:str
    platform:str
    content_type:str

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
    thread_id = f"content-{request.topic.lower().replace(' ', '-')}-{request.platform.lower()}"
    result = graph.invoke(
        {
            "topic": request.topic,
            "platform": request.platform,
            "content_type": request.content_type,
            "ideas": [],
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    review_interrupt = result.get("__interrupt__")
    final_content = result.get("final_content") or result.get("generated_content")

    return {
        "thread_id": thread_id,
        "content_id": result.get("content_id"),
        "idea": result.get("selected_idea"),
        "platform": result.get("platform"),
        "content_type": result.get("content_type"),
        "content": final_content,
        "quality_score": result.get("quality_score"),
        "refinement_count": result.get("refinement_count"),
        "requires_review": bool(review_interrupt),
        "interrupt": review_interrupt,
    }


@router.post("/ideas")
def generate_ideas(request: IdeaRequest):
    thread_id = f"ideas-{request.topic.lower().replace(' ', '-')}-{request.platform.lower()}"
    result = graph.invoke(
        {
            "topic": request.topic,
            "platform": request.platform,
            "content_type": request.content_type,
            "ideas": [],
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    return {
        "topic": request.topic,
        "platform": request.platform,
        "content_type": request.content_type,
        "research_required": result.get("research_required", False),
        "research_results": result.get("research_results", []),
        "ideas": result.get("ideas", []),
    }

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
        result = list_knowledge()
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/content/history")
def list_generated_content():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT
            id,
            idea_id,
            platform,
            content_type,
            content,
            quality_score,
            status,
            approved_at,
            published_at,
            publish_status,
            external_post_id,
            publish_error,
            created_at
        FROM generated_content
        ORDER BY created_at DESC
        """
    ).fetchall()
    connection.close()
    return {"items": [dict(row) for row in rows]}


@router.get("/content/{content_id}")
def get_generated_content(content_id: int):
    connection = get_connection()
    row = connection.execute(
        """
        SELECT
            id,
            idea_id,
            platform,
            content_type,
            content,
            quality_score,
            status,
            approved_at,
            published_at,
            publish_status,
            external_post_id,
            publish_error,
            created_at
        FROM generated_content
        WHERE id = ?
        """,
        (content_id,),
    ).fetchone()
    connection.close()

    if row is None:
        return {"error": "Content not found"}

    return dict(row)

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