from app.core.llm import llm
from app.models.content import GeneratedContent


structured_llm = llm.with_structured_output(GeneratedContent)


def generate_content(
    idea: dict,
    platform: str,
    content_type: str,
    personal_context: list,
    research_results: list,
) -> str:

    personal_text = "\n\n".join(
        item.get("chunk_text", "")
        for item in personal_context
    )

    research_text = "\n\n".join(
        f"Source: {item.get('title')}\n"
        f"URL: {item.get('url')}\n"
        f"{item.get('content')}"
        for item in research_results
    )

    prompt = f"""
You are an AI content writer helping a technical AI engineer
create authentic social media content.

PLATFORM:
{platform}

CONTENT TYPE:
{content_type}

CONTENT IDEA:
Title: {idea.get("title")}
Angle: {idea.get("angle")}
Reason: {idea.get("reason")}

PERSONAL KNOWLEDGE:
{personal_text}

WEB RESEARCH:
{research_text}

Write a high-quality {platform} post.

Rules:

1. Do not invent personal experiences.
2. Do not claim the user built something unless it appears
   in the provided personal knowledge.
3. Use web research only when making factual/current claims.
4. Do not blindly copy research sources.
5. Make the writing sound human rather than corporate.
6. Avoid generic AI-generated introductions.
7. Give the reader something useful.
8. Match the platform.

For X:
- Be concise.
- Make the hook strong.
- Use short sentences.
- Avoid unnecessary hashtags.
- If the topic needs multiple posts, structure it as a thread.

For LinkedIn:
- Use short paragraphs.
- Make it easy to scan.
- Explain technical concepts clearly.
- Avoid excessive corporate language.
- End with a meaningful takeaway.

Return only the final post content.
"""

    result = structured_llm.invoke(prompt)

    return result.content