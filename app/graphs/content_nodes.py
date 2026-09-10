from app.core.llm import llm
from app.graphs.content_state import ContentState
from app.models.content import ContentIdeas
from app.services.content_service import save_ideas
from app.services.retrieval_service import (
    retrieve_relevant_chunks,
)
from app.tools.web_search import web_search
structured_llm = llm.with_structured_output(ContentIdeas)

def generate_content_ideas(state: ContentState) -> ContentState:

    topic = state["topic"]
    platform = state["platform"]
    content_type = state["content_type"]
    personal_context = "\n\n".join(
    result["text"]
    for result in state.get(
        "retrieved_context",
        []
    )
)

    research_context = "\n\n".join(
    result["content"]
    for result in state.get(
        "research_results",
        []
    )
)
    prompt = f"""
You are a content strategist helping me grow my personal brand.

PERSONAL KNOWLEDGE:
{personal_context}

WEB RESEARCH:
{research_context}

Use personal knowledge when discussing
my experiences.

Use web research when discussing
current facts or developments.

Do not invent personal experiences.

Do not present unsupported claims as facts.

Make the ideas specific and useful.


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

WEB RESEARCH RULES:

- Use web research only for factual/current claims.
- Do not fabricate facts.
- Prefer information supported by multiple sources.
- Do not treat search snippets as unquestionable truth.
- If sources disagree, do not hide the disagreement.
- Keep the source URLs associated with relevant claims.

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

def retrieve_personal_knowledge(
    state: ContentState
) -> ContentState:

    topic = state["topic"]

    results = retrieve_relevant_chunks(
        query=topic,
        top_k=5,
    )

    return {
        **state,
        "retrieved_context": results,
    }
# this nodes is given the state and decides if research is required based on the content type and topic. It sets the research_required flag and the research_query accordingly.
def decide_research(
    state: ContentState
) -> ContentState:

    content_type = state["content_type"]

    topic = state["topic"]

    # AI news almost always requires current information.
    if content_type == "ai_news":

        return {
            **state,
            "research_required": True,
            "research_query": topic,
        }

    # For personal/build-in-public content,
    # your own knowledge is usually more important.
    if content_type == "build_in_public":

        return {
            **state,
            "research_required": False,
            "research_query": "",
        }

    # Technical and opinion content may benefit
    # from current information.
    if content_type in [
        "technical",
        "opinion",
    ]:

        return {
            **state,
            "research_required": True,
            "research_query": topic,
        }

    return {
        **state,
        "research_required": False,
        "research_query": "",
    }

def research_topic(
    state: ContentState
) -> ContentState:

    query = state["research_query"]

    results = web_search.invoke({
        "query": query
    })

    return {
        **state,
        "research_results": results,
    }
# this code block act as the router to determine if reasearch is required or not. If research is required, it will call the research_topic node, otherwise it will return the state as is.
def research_router(
    state: ContentState
):

    if state["research_required"]:
        return "research"

    return "generate"
# this nodes is used to generate a concise query for web search to avoid ambiguity 
def generate_research_query(
    state: ContentState
) -> ContentState:

    topic = state["topic"]

    content_type = state["content_type"]

    prompt = f"""
Create one concise web search query.

Topic:
{topic}

Content type:
{content_type}

The query should retrieve reliable and
current information useful for creating
social media content.

Return only the search query.
"""

    response = llm.invoke(prompt)
    research_query = response.content[0]["text"].strip()

    return {
        **state,
        "research_query": research_query,
    }