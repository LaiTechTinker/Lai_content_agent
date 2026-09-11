from pydantic import BaseModel, Field
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
    content_id: int
    human_action: str
    human_feedback: str
    edited_content: str
    approval_status: str
    media_requested: bool
    image_requested: bool
    audio_requested: bool
    image_url: str
    audio_url: str

