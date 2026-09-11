from app.tools.audio_generate import generate_audio
model_name=""
def generate_audio(text: str) -> str:
    """
    Convert text into speech.

    Returns the generated audio file path or URL.
    """
    try:
        audio_path=generate_audio(text=text,model_name=model_name)
        return audio_path
    except Exception as e:
        return f"error occured:{str(e)}"


    
    