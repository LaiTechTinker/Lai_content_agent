from pydantic import BaseModel
from typing import TypedDict


class ContentState(TypedDict):
    topic: str
    platform: str
    content_type:str
    saved_ids:list
    ideas: list[str]
    retrieved_context: list
    research_required: bool
    research_query: str
    research_results: list
    selected_idea: dict

    generated_content: str

    quality_score: int
    quality_feedback: str

    refinement_count: int

    final_content: str