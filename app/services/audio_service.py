from app.tools.audio_generate import generate_audio as generate_audio_file
from app.core.config import settings


def generate_audio(text: str) -> str:
    """Convert text into speech and return the output path."""
    if not settings.audio_model:
        raise RuntimeError("Audio generation model is not configured.")
    audio_path = generate_audio_file(text=text, model_name=settings.audio_model)
    if not audio_path:
        raise RuntimeError("Audio provider returned no file.")
    return audio_path