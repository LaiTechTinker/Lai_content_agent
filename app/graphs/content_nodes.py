from app.core.llm import llm
from app.graphs.content_state import ContentState


def generate_content_ideas(state: ContentState) -> ContentState:

    topic = state["topic"]
    platform = state["platform"]

    prompt = f"""
You are a content strategist helping me grow my personal brand.

Generate 5 strong content ideas.

Topic:
{topic}

Platform:
{platform}

My content focuses on:
- AI engineering
- AI agents
- Machine learning
- Building projects in public
- Technical explanations
- AI opinions
- AI industry developments

For each idea provide:
1. A compelling title
2. The core angle
3. Why someone would care

Avoid generic ideas such as:
"10 AI trends you need to know."

Make the ideas specific and useful.
"""

    response = llm.invoke(prompt)

    return {
        **state,
        "ideas": [response.content],
    }