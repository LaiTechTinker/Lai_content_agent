from app.core.llm import llm


def generate_image_prompt(
    content: str,
    platform: str,
) -> str:

    prompt = f"""
Create a detailed visual prompt for an image
that accompanies this social media post.

Platform:
{platform}

Post:
{content}

Requirements:

- The image should communicate the main idea visually.
- Do not put large paragraphs of text inside the image.
- Avoid generic corporate stock-photo aesthetics.
- Prefer a clean editorial or technical visual style.
- The image should complement the post rather than repeat it.
- Do not invent specific people or personal experiences.
- Do not include logos unless explicitly requested.

Return only the image-generation prompt.
"""

    response = llm.invoke(prompt)

    return response.content