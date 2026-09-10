from langgraph.graph import END,START,StateGraph
from app.graphs.content_nodes import (generate_content_ideas,
                                      quality_check,save_ideas_node,retrieve_personal_knowledge)
                                      
from app.graphs.content_state import ContentState




# this section build the graph for content generation

def build_content_graph():
    graph=StateGraph(ContentState)
    graph.add_node(
        "retrieve_personal_knowledge",
        retrieve_personal_knowledge
    )
    graph.add_node("generate_content_ideas",generate_content_ideas)
    graph.add_node("quality_check",quality_check)
    graph.add_node("save_ideas_node",save_ideas_node)
    graph.add_node()
    graph.add_edge(
        START,
        "retrieve_personal_knowledge"
    )
    graph.add_edge("retrieve_personal_knowledge","generate_content_ideas")
    graph.add_edge("generate_content_ideas","quality_check")
    graph.add_edge("quality_check","save_ideas_node")
    graph.add_edge("save_ideas_node",END)
    return graph.compile()

