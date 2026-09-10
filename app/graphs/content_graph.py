from langgraph import graph
from langgraph.graph import END,START,StateGraph
from app.graphs.content_nodes import (generate_content_ideas,
                                      quality_check,save_ideas_node,
                                      retrieve_personal_knowledge,decide_research,research_topic,
                                      research_router,generate_research_query,generate_content_node,
    evaluate_content_node,
    refine_content_node,
    content_quality_router,save_generated_content_node)

from app.graphs.human_reveiw import (
    human_review_node,
    finalize_human_review_node,
    save_approval_node,
)
from app.db.checkpointer import checkpointer
                                      
from app.graphs.content_state import ContentState




# this section build the graph for content generation

def build_content_graph():
    graph=StateGraph(ContentState)
    graph.add_node(
        "retrieve_personal_knowledge",
        retrieve_personal_knowledge
    )
    graph.add_node(
        "decide_research",
        decide_research
    )
    graph.add_node(
        "generate_research_query",
        generate_research_query
    )

    graph.add_node(
        "research",
        research_topic
    )
    graph.add_node("generate_content_ideas",generate_content_ideas)
    graph.add_node("quality_check",quality_check)
    graph.add_node("save_ideas_node",save_ideas_node)
    graph.add_node(
    "generate_content",
    generate_content_node,
)

    graph.add_node(
    "evaluate_content",
    evaluate_content_node,
)

    graph.add_node(
    "refine_content",
    refine_content_node,
)
    graph.add_node(
    "save_generated_content",
    save_generated_content_node,
)
    graph.add_node(
    "human_review",
    human_review_node,
)

    graph.add_node(
    "finalize_human_review",
    finalize_human_review_node,
)

    graph.add_node(
    "save_approval",
    save_approval_node,
)
    graph.add_edge(
        START,
        "retrieve_personal_knowledge"
    )
    graph.add_edge(
        "retrieve_personal_knowledge",
        "decide_research"
    )
    graph.add_conditional_edges(
        "decide_research", #this represent the node that will decide the next step based on the research_required flag
        research_router,
        {
            "research": "generate_research_query",
            "generate": "generate_content_ideas",
        },
    )
    graph.add_edge(
        "generate_research_query",
        "research"
    )
    graph.add_edge(
        "research",
        "generate_content_ideas"
    )
    # graph.add_edge("retrieve_personal_knowledge","generate_content_ideas")
    graph.add_edge("generate_content_ideas","quality_check")
    graph.add_edge("quality_check","save_ideas_node")
    graph.add_edge(
    "save_ideas_node",
    "generate_content",
)

    graph.add_edge(
    "generate_content",
    "evaluate_content",
) 
    graph.add_conditional_edges(
    "evaluate_content",
    content_quality_router,
    {
        "refine": "refine_content",
        "approved": "save_generated_content",
    },
)

    graph.add_edge(
    "refine_content",
    "evaluate_content",
)
    graph.add_edge(
    "save_generated_content",
    "human_review",
)

    graph.add_edge(
    "human_review",
    "finalize_human_review",
)
    graph.add_edge(
    "finalize_human_review",
    "save_approval",
)

    graph.add_edge(
    "save_approval",
    END,
)

  
   
    return graph.compile(checkpointer=checkpointer)

