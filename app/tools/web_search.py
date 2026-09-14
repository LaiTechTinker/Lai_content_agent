from tavily import TavilyClient
from langchain_core.tools import tool

from app.core.config import settings


client = TavilyClient(
    api_key=settings.tavily_api_key
)


@tool
def web_search(query: str) -> list[dict]:
    """
    Search the web for current information relevant
    to the user's content topic.
    """

    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
    )

    results = response.get("results", [])

    return [
        {
            "title": result.get("title"),
            "url": result.get("url"),
            "content": result.get("content"),
        }
        for result in results
    ]
