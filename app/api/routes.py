from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import UploadFile, File
import tempfile
import os
from app.graphs.content_graph import build_content_graph
from app.services.document_service import (
    ingest_document,
)
from app.db.database import list_knowledge

# this initialize our router
router=APIRouter()
# this inititialize our graph
graph=build_content_graph()


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
def generate_content(request:IdeaRequest):
    result=graph.invoke({
        "topic":request.topic,
        "platform":request.platform,
        "content_type":request.content_type
    })
    return {
    "content_id": result.get("content_id"),
    "idea": result.get("selected_idea"),
    "platform": result.get("platform"),
    "content_type": result.get("content_type"),
    "content": result.get("final_content"),
    "quality_score": result.get("quality_score"),
    "refinement_count": result.get("refinement_count"),
}


@router.post("/ideas")
def generate_ideas(request:IdeaRequest):
    result=graph.invoke({
        "topic":request.topic,
        "platform":request.platform,
        "content_type":request.content_type,
        "ideas":[]
    })
    return {
    "topic": request.topic,
    "platform": request.platform,
    "content_type": request.content_type,
    "research_required": result[
        "research_required"
    ],
    "research_results": result.get(
        "research_results",
        []
    ),
    "ideas": result["ideas"],
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
       result=list_knowledge()

       return result
   except Exception as e:
       return {"error":str(e)}
    
       

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