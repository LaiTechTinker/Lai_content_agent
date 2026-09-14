# this is a file serving as an utils for generating image using diffrent image providers(gemini,openAI image2)
from uuid import uuid1
from google import genai
from PIL import Image
import base64
import requests
from app.core.config import settings

WORKER_URL = settings.cloudflare_url
cloudflare_api = settings.cloudflare_secret
client = genai.Client(api_key=settings.require_google_api_key())



def generate_image_with_nano(prompt:str,model_name:str):
    interaction = client.interactions.create(
    model=model_name,
    input=prompt,
)
    image_path=f"{uuid1()}.png"
    with open(image_path,"wb") as f:
        f.write(base64.b64decode(interaction.output_image.data))
    return image_path

def generate_with_cloud(prompt:str):
 try:
    headers = {
    "Authorization": f"Bearer {cloudflare_api}",
    "Content-Type": "application/json",
}

    if not WORKER_URL or not cloudflare_api:
        raise RuntimeError("CLOUDFLARE_SECRET and CLOUDFLARE_URL are required for Cloudflare image generation.")
    response = requests.post(
    WORKER_URL,
    headers=headers,
    json={"prompt": prompt},
    timeout=120,
)
    image_path=f"{uuid1()}.jpg"
    if not response.ok:
        raise RuntimeError(
            f"Image provider failed: {response.status_code} {response.text}"
        )

    with open(image_path, "wb") as file:
        file.write(response.content)

    return image_path
 except Exception as e:
  return f"Error occured:{str(e)}" 