# this is a file serving as an utils for generating image using diffrent image providers(gemini,openAI image2)
import os
from uuid import uuid1
from google import genai
from dotenv import load_dotenv
from PIL import Image
import base64
load_dotenv()
api_key=os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)



def generate_image_with_nano(prompt:str,model_name:str):
    interaction = client.interactions.create(
    model=model_name,
    input=prompt,
)
    image_path=f"{uuid1()}.png"
    with open(image_path,"wb") as f:
        f.write(base64.b64decode(interaction.output_image.data))
    return image_path
