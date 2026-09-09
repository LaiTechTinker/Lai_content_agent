from langgraph.graph import END,START,StateGraph
from app.graphs.content_nodes import generate_content_ideas
from app.graphs.content_state import ContentState



# this section build the graph for content generation

def build_content_graph():
    graph=StateGraph(ContentState)
    graph.add_node("generate_content_ideas",generate_content_ideas)
    graph.add_edge(START,"generate_content_ideas")
    graph.add_edge("generate_content_ideas",END)
    return graph.compile()

