from langgraph.types import Command

from app.graphs.content_graph import graph


def test_human_review():

    config = {
        "configurable": {
            "thread_id": "test-content-001"
        }
    }

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

    resumed = graph.invoke(
        Command(
            resume={
                "action": "edit",
                "content": (
                    "My edited version of the AI agent post."
                ),
            }
        ),
        config=config,
    )

    print("RESUMED RESULT:")
    print(resumed)