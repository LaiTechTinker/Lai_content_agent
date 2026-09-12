from app.graphs.content_graph import build_content_graph

graph = build_content_graph()
config = {"configurable": {"thread_id": "test-content-graph"}}

result = graph.invoke(
    {
        "topic": "Learning LangGraph",
        "platform": "X",
        "content_type": "technical",
        "ideas": [],
    },
    config=config,
)

print(result)