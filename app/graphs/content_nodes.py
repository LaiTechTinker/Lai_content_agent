from app.core.llm import llm
from app.graphs.content_state import ContentState
from app.models.content import ContentIdeas
from app.services.content_service import save_ideas

structured_llm = llm.with_structured_output(ContentIdeas)

def generate_content_ideas(state: ContentState) -> ContentState:

    topic = state["topic"]
    platform = state["platform"]
    content_type = state["content_type"]

    prompt = f"""
You are a content strategist helping me grow my personal brand.

Generate 5 strong content ideas.

Topic:
{topic}

Platform:
{platform}

content_type:
{content_type}

My content focuses on:
- AI engineering
- AI agents
- Machine learning
- Building projects in public
- Technical explanations
- AI opinions
- AI industry developments

For each idea provide:
- A compelling title
- A specific angle
- Why the idea is valuable

Avoid generic content.

The ideas should sound like something a technical
AI engineer could genuinely post about.
"""

    result = structured_llm.invoke(prompt)

    return {
        **state,
        "ideas": result.ideas,
    }

# let's add a placeholder function that validates my ideas

def quality_check(state: ContentState) -> ContentState:

    ideas = state["ideas"]

    valid_ideas = []

    for idea in ideas:

        if not idea.title.strip():
            continue

        if not idea.angle.strip():
            continue

        if not idea.reason.strip():
            continue

        valid_ideas.append(idea)

    return {
        **state,
        "ideas": valid_ideas,
    }

# this saves the ideas to database
def save_ideas_node(state: ContentState) -> ContentState:

    ids = save_ideas(
        topic=state["topic"],
        ideas=state["ideas"],
    )

    return {
        **state,
        "saved_ids": ids,
    }