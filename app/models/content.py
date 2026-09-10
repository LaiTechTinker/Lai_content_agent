from pydantic import BaseModel, Field
from typing import Literal


ContentType = Literal[
    "build_in_public",
    "technical",
    "opinion",
    "ai_news",
]

Platform = Literal[
    "X",
    "LinkedIn",
]


class ContentIdea(BaseModel):
    title: str = Field(
        description="A compelling title or hook for the content idea"
    )

    angle: str = Field(
        description="The specific perspective or argument of the idea"
    )

    reason: str = Field(
        description="Why this idea would be valuable to the audience"
    )

    content_type: ContentType

    platform: Platform


class ContentIdeas(BaseModel):
    ideas: list[ContentIdea]



class GeneratedContent(BaseModel):
    content: str


class ContentEvaluation(BaseModel):
    score: int = Field(ge=1, le=10)
    feedback: str
    should_refine: bool