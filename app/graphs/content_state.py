from pydantic import BaseModel
from typing import TypeDict


class ContentState(TypeDict):
    topic: str
    platform: str
    ideas: list[str]