from pydantic import BaseModel
from typing import TypedDict


class ContentState(TypedDict):
    topic: str
    platform: str
    content_type:str
    saved_ids:list
    ideas: list[str]