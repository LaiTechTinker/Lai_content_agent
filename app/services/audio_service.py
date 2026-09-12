import os

from app.tools.audio_generate import generate_audio as generate_audio_file

MODEL_NAME = os.getenv("AUDIO_MODEL", "")


def generate_audio(text: str) -> str:
    """Convert text into speech and return the output path."""
    if not MODEL_NAME:
        raise RuntimeError("Audio generation model is not configured.")
    audio_path = generate_audio_file(text=text, model_name=MODEL_NAME)
    if not audio_path:
        raise RuntimeError("Audio provider returned no file.")
    return audio_path