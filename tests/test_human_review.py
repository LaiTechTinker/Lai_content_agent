from langgraph.types import Command

from app.graphs.content_graph import graph


def test_human_review():
    config = {"configurable": {"thread_id": "content-123"}}

    result = graph.invoke(
        {
            "topic": "What I learned building an AI agent",
            "platform": "X",
            "content_type": "technical",
        },
        config=config,
    )

    print("FIRST RESULT:")
    print(result)

    selected = graph.invoke(
        Command(
            resume={
                "action": "select_idea",
                "selected_idea_id": result["saved_ids"][0],
            }
        ),
        config=config,
    )

    print("SELECTED IDEA RESULT:")
    print(selected)

    resumed = graph.invoke(
        Command(
            resume={
                "action": "edit",
                "content": "My edited version of the AI agent post.",
            }
        ),
        config=config,
    )

    print("RESUMED RESULT:")
    print(resumed)