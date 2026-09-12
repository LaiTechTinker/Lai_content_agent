import os

from app.tools.audio_generate import generate_audio as generate_audio_file

MODEL_NAME = os.getenv("AUDIO_MODEL", "")


def generate_audio(text: str) -> str:
    """Convert text into speech and return the output path or a placeholder."""
    if not MODEL_NAME:
        return "audio_not_configured"
    try:
        return generate_audio_file(text=text, model_name=MODEL_NAME)
    except Exception as e:
        return f"error occured:{str(e)}"