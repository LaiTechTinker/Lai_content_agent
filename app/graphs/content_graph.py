from langgraph.graph import END, START, StateGraph

from app.db.checkpointer import checkpointer
from app.graphs.content_nodes import (
    content_quality_router,
    decide_research,
    evaluate_content_node,
    generate_content_ideas,
    generate_content_node,
    generate_research_query,
    quality_check,
    research_router,
    research_topic,
    retrieve_personal_knowledge,
    refine_content_node,
    save_generated_content_node,
    save_ideas_node,
)
from app.graphs.content_state import ContentState
from app.graphs.human_reveiw import (
    finalize_human_review_node,
    human_review_node,
    save_approval_node,
)
from app.graphs.media_nodes import (
    audio_router,
    audio_skipped_node,
    generate_audio_node,
    generate_image_node,
    image_router,
    image_skipped_node,
)


def _audio_decision_node(state):
    return state


def build_content_graph():
    graph = StateGraph(ContentState)

    graph.add_node("retrieve_personal_knowledge", retrieve_personal_knowledge)
    graph.add_node("decide_research", decide_research)
    graph.add_node("generate_research_query", generate_research_query)
    graph.add_node("research", research_topic)
    graph.add_node("generate_content_ideas", generate_content_ideas)
    graph.add_node("quality_check", quality_check)
    graph.add_node("save_ideas_node", save_ideas_node)
    graph.add_node("generate_content", generate_content_node)
    graph.add_node("evaluate_content", evaluate_content_node)
    graph.add_node("refine_content", refine_content_node)
    graph.add_node("save_generated_content", save_generated_content_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("finalize_human_review", finalize_human_review_node)
    graph.add_node("save_approval", save_approval_node)
    graph.add_node("generate_image", generate_image_node)
    graph.add_node("image_skipped", image_skipped_node)
    graph.add_node("audio_decision", _audio_decision_node)
    graph.add_node("generate_audio", generate_audio_node)
    graph.add_node("audio_skipped", audio_skipped_node)

    graph.add_edge(START, "retrieve_personal_knowledge")
    graph.add_edge("retrieve_personal_knowledge", "decide_research")
    graph.add_conditional_edges(
        "decide_research",
        research_router,
        {
            "research": "generate_research_query",
            "generate": "generate_content_ideas",
        },
    )
    graph.add_edge("generate_research_query", "research")
    graph.add_edge("research", "generate_content_ideas")
    graph.add_edge("generate_content_ideas", "quality_check")
    graph.add_edge("quality_check", "save_ideas_node")
    graph.add_edge("save_ideas_node", "generate_content")
    graph.add_edge("generate_content", "evaluate_content")
    graph.add_conditional_edges(
        "evaluate_content",
        content_quality_router,
        {
            "refine": "refine_content",
            "approved": "save_generated_content",
        },
    )
    graph.add_edge("refine_content", "evaluate_content")
    graph.add_edge("save_generated_content", "human_review")
    graph.add_edge("human_review", "finalize_human_review")
    graph.add_edge("finalize_human_review", "save_approval")
    graph.add_conditional_edges(
        "save_approval",
        image_router,
        {
            "generate_image": "generate_image",
            "skip_image": "image_skipped",
        },
    )
    graph.add_edge("generate_image", "audio_decision")
    graph.add_edge("image_skipped", "audio_decision")
    graph.add_conditional_edges(
        "audio_decision",
        audio_router,
        {
            "generate_audio": "generate_audio",
            "skip_audio": "audio_skipped",
        },
    )
    graph.add_edge("generate_audio", END)
    graph.add_edge("audio_skipped", END)

    compiled = graph.compile(checkpointer=checkpointer)
    return compiled


graph = build_content_graph()
