from langgraph.graph import END, START, StateGraph

from app.db.checkpointer import checkpointer
from app.graphs.content_nodes import (
    content_quality_router,
    decide_research,
    evaluate_content_node,
    generate_content_ideas,
    generate_content_node,
    generate_research_query,
    research_router,
    research_topic,
    retrieve_personal_knowledge,
    refine_content_node,
    save_generated_content_node,
    save_ideas_node,
    initialize_request,
    human_select_idea_node,
    validate_ideas,
)
from app.graphs.content_state import ContentState
from app.graphs.human_reveiw import (
    finalize_human_review_node,
    human_review_node,
    review_action_router,
    save_rejection_node,
    save_approval_node,
)
from app.graphs.media_nodes import (
    audio_decision_node,
    audio_review_node,
    audio_review_router,
    generate_audio_node,
    generate_image_node,
    image_decision_node,
    image_review_node,
    image_review_router,
    save_final_content_node,
)


def build_content_graph():
    graph = StateGraph(ContentState)

    graph.add_node("initialize_request", initialize_request)
    graph.add_node("retrieve_personal_context", retrieve_personal_knowledge)
    graph.add_node("decide_research", decide_research)
    graph.add_node("generate_research_query", generate_research_query)
    graph.add_node("research", research_topic)
    graph.add_node("generate_content_ideas", generate_content_ideas)
    graph.add_node("validate_ideas", validate_ideas)
    graph.add_node("save_ideas", save_ideas_node)
    graph.add_node("human_select_idea", human_select_idea_node)
    graph.add_node("generate_content", generate_content_node)
    graph.add_node("evaluate_content", evaluate_content_node)
    graph.add_node("refine_content", refine_content_node)
    graph.add_node("save_generated_content", save_generated_content_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("finalize_human_review", finalize_human_review_node)
    graph.add_node("save_approval", save_approval_node)
    graph.add_node("save_rejection", save_rejection_node)
    graph.add_node("image_decision", image_decision_node)
    graph.add_node("generate_image", generate_image_node)
    graph.add_node("image_review", image_review_node)
    graph.add_node("audio_decision", audio_decision_node)
    graph.add_node("generate_audio", generate_audio_node)
    graph.add_node("audio_review", audio_review_node)
    graph.add_node("save_final_content", save_final_content_node)

    graph.add_edge(START, "initialize_request")
    graph.add_edge("initialize_request", "retrieve_personal_context")
    graph.add_edge("retrieve_personal_context", "decide_research")
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
    graph.add_edge("generate_content_ideas", "validate_ideas")
    graph.add_edge("validate_ideas", "save_ideas")
    graph.add_edge("save_ideas", "human_select_idea")
    graph.add_edge("human_select_idea", "generate_content")
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
    graph.add_conditional_edges(
        "human_review",
        review_action_router,
        {
            "approve": "finalize_human_review",
            "reject": "save_rejection",
        },
    )
    graph.add_edge("finalize_human_review", "save_approval")
    graph.add_edge("save_approval", "image_decision")
    graph.add_edge("save_rejection", END)
    graph.add_conditional_edges(
        "image_decision",
        lambda state: "generate" if state.get("image_decision") == "generate" else "audio",
        {"generate": "generate_image", "audio": "audio_decision"},
    )
    graph.add_edge("generate_image", "image_review")
    graph.add_conditional_edges(
        "image_review",
        image_review_router,
        {"regenerate": "generate_image", "audio": "audio_decision"},
    )
    graph.add_conditional_edges(
        "audio_decision",
        lambda state: "generate" if state.get("audio_decision") == "generate" else "finish",
        {"generate": "generate_audio", "finish": "save_final_content"},
    )
    graph.add_edge("generate_audio", "audio_review")
    graph.add_conditional_edges(
        "audio_review",
        audio_review_router,
        {"regenerate": "generate_audio", "finish": "save_final_content"},
    )
    graph.add_edge("save_final_content", END)

    compiled = graph.compile(checkpointer=checkpointer)
    return compiled


graph = build_content_graph()
