import os
from pathlib import Path
from app.tools.image_generate import generate_image_with_nano
model_name=""

def generate_image(prompt: str) -> str:
    """
    Generate an image and return its local file path.

    The actual provider implementation will live here.
    """
    try:
      image_path=generate_image_with_nano(prompt=prompt,model_name=model_name)
      return image_path

    except Exception as e:
       return f"Error occured:{str(e)}"

  