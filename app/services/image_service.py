import os

from app.tools.image_generate import (generate_image_with_nano,generate_with_cloud)

MODEL_NAME = os.getenv("IMAGE_MODEL", "")

USE_GEMINI=False

def generate_image(prompt: str) -> str:
  """Generate an image and return its local file path or URL."""
  if USE_GEMINI:
    if not MODEL_NAME:
      raise RuntimeError("Image generation model is not configured.")
    image_path = generate_image_with_nano(
      prompt=prompt,
      model_name=MODEL_NAME,
    )
  else:
    image_path = generate_with_cloud(prompt=prompt)

  if not image_path or str(image_path).lower().startswith("error"):
    raise RuntimeError(str(image_path or "Image provider returned no file."))
  return image_path
