from typing import Any, NotRequired, TypedDict


class ContentState(TypedDict):
    topic: str
    platform: str
    content_type: str
    original_prompt: NotRequired[str]
    saved_ids: NotRequired[list[int]]
    ideas: NotRequired[list[Any]]
    retrieved_context: NotRequired[list]
    research_required: NotRequired[bool]
    research_query: NotRequired[str]
    research_results: NotRequired[list]
    selected_idea: NotRequired[Any]
    selected_idea_id: NotRequired[int]
    generated_content: NotRequired[str]
    evaluation: NotRequired[dict]
    quality_score: NotRequired[int]
    quality_feedback: NotRequired[str]
    refinement_count: NotRequired[int]
    final_content: NotRequired[str]
    content_id: NotRequired[int]
    human_action: NotRequired[str]
    human_feedback: NotRequired[str]
    edited_content: NotRequired[str]
    approval_status: NotRequired[str]
    workflow_stage: NotRequired[str]
    thread_id: NotRequired[str]
    image_decision: NotRequired[str]
    image_status: NotRequired[str]
    image_url: NotRequired[str | None]
    image_attempt_count: NotRequired[int]
    image_error: NotRequired[str | None]
    image_media_id: NotRequired[int]
    audio_decision: NotRequired[str]
    audio_status: NotRequired[str]
    audio_url: NotRequired[str | None]
    audio_attempt_count: NotRequired[int]
    audio_error: NotRequired[str | None]
    audio_media_id: NotRequired[int]

