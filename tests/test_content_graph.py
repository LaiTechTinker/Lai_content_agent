from app.graphs.content_graph import build_content_graph

graph = build_content_graph()


result = graph.invoke({
    "topic": "Learning LangGraph",
    "platform": "X",
    "ideas": []
})


print(result)