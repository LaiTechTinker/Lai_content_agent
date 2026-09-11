import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def generate_image(prompt: str) -> str:
    """
    Generate an image and return its local file path.

    The actual provider implementation will live here.
    """

    raise NotImplementedError(
        "Connect your selected image-generation provider here."
    )