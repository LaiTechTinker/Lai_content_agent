from app.core.config import settings
from app.tools.image_generate import generate_image_with_nano, generate_with_cloud

def generate_image(prompt: str) -> str:
  """Generate an image and return its local file path or URL."""
  if settings.use_gemini_image:
    if not settings.image_model:
      raise RuntimeError("Image generation model is not configured.")
    image_path = generate_image_with_nano(
      prompt=prompt,
      model_name=settings.image_model,
    )
  else:
    image_path = generate_with_cloud(prompt=prompt)

  if not image_path or str(image_path).lower().startswith("error"):
    raise RuntimeError(str(image_path or "Image provider returned no file."))
  return image_path
