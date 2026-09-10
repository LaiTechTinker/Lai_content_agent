from fastapi import APIRouter
from pydantic import BaseModel
from app.graphs.content_graph import build_content_graph
# from app.db.database import get_idea_by_id

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

@router.post("/ideas")
def generate_ideas(request:IdeaRequest):
    result=graph.invoke({
        "topic":request.topic,
        "platform":request.platform,
        "content_type":request.content_type,
        "ideas":[]
    })
    return  {
        "topic": request.topic,
        "platform": request.platform,
        "ideas": result["ideas"]
    }

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