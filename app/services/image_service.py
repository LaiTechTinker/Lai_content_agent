import os

from app.tools.image_generate import (generate_image_with_nano,generate_with_cloud)

MODEL_NAME = os.getenv("IMAGE_MODEL", "")

USE_GEMINI=False

def generate_image(prompt: str) -> str:
    """Generate an image and return its local file path."""
    try:
     
     if USE_GEMINI:
       if not MODEL_NAME:
         return "image_not_configured"
       image_path=generate_image_with_nano(prompt=prompt, model_name=MODEL_NAME)
       return image_path
     else:
        image_path=generate_with_cloud(prompt=prompt)
        return image_path
   
        
    except Exception as e:
        return f"Error occured:{str(e)}"
  