from google import genai
import os
from dotenv import load_dotenv
from uuid import uuid4
import wave
import base64
load_dotenv()

api_key=os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def generate_audio(text:str,model_name:str):
    interaction = client.interactions.create(
    model=model_name,
    input=text,
    response_format={"type": "audio"},
    generation_config={
        "speech_config": [
            {"voice": "Kore"}
        ]
    }
)
    audio_path=f"{str(uuid4())}.wav"
    wave_file(audio_path, base64.b64decode(interaction.output_audio.data))
    return audio_path


