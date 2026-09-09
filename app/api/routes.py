from fastapi import APIRouter
from pydantic import BaseModel
from app.graphs.content_graph import build_content_graph

# this initialize our router
router=APIRouter()
# this inititialize our graph
graph=build_content_graph()


class IdeaRequest(BaseModel):
    topic:str
    platform:str
    content_type:str


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