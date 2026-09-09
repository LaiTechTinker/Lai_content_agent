from pydantic import BaseModel
from typing import TypedDict


class ContentState(TypedDict):
    topic: str
    platform: str
    ideas: list[str]