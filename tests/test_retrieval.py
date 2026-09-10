from app.services.retrieval_service import (
    retrieve_relevant_chunks,
)


results = retrieve_relevant_chunks(
    "What did I learn about LangGraph?"
)

for result in results:

    print("\n---")
    print("Score:", result["score"])
    print(result["text"])