from app.services.media_prompt_service import (
    generate_image_prompt,
)

from app.services.image_service import (
    generate_image,
)

from app.services.media_service import (
    save_media,
)
from app.services.audio_service import (
    generate_audio,
)


def generate_image_node(state):

    content = state.get("final_content")

    if not content:
        raise ValueError(
            "Cannot generate image without final content."
        )

    prompt = generate_image_prompt(
        content=content,
        platform=state["platform"],
    )

    image_url = generate_image(prompt)

    save_media(
        content_id=state["content_id"],
        media_type="image",
        media_url=image_url,
    )

    return {
        "image_url": image_url,
    }




def generate_audio_node(state):

    content = state.get("final_content")

    if not content:
        raise ValueError(
            "Cannot generate audio without final content."
        )

    audio_url = generate_audio(content)

    save_media(
        content_id=state["content_id"],
        media_type="audio",
        media_url=audio_url,
    )

    return {
        "audio_url": audio_url,
    }
# this will be used for our conditional routing
def media_router(state):

    image_requested = state.get(
        "image_requested",
        False,
    )

    audio_requested = state.get(
        "audio_requested",
        False,
    )

    if image_requested:
        return "image"

    if audio_requested:
        return "audio"

    return "finish"

def image_router(state):

    if state.get("image_requested", False):
        return "generate_image"

    return "skip_image"

def audio_router(state):

    if state.get("audio_requested", False):
        return "generate_audio"

    return "skip_audio"