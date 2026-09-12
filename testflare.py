# import requests
# import os
# from dotenv import load_dotenv
# load_dotenv()
# WORKER_URL = "https://zubaimage.ibrahimalaaya7.workers.dev/"
# API_KEY = os.getenv("CLOUDFLARE_SCERET")

# prompt = """
# Create a modern professional educational infographic about AI Agents, inspired by the attached reference. Use a dark navy background, bold white and purple typography, clean glowing AI/technology illustrations, clear numbered sections, arrows showing the process, and concise bullet points. Make it visually polished, minimal, highly readable, and suitable for LinkedIn/Instagram.
# """

# headers = {
#     "Authorization": f"Bearer {API_KEY}",
#     "Content-Type": "application/json",
# }

# response = requests.post(
#     WORKER_URL,
#     headers=headers,
#     json={"prompt": prompt},
#     timeout=120,
# )

# print("Status:", response.status_code)
# print("Content-Type:", response.headers.get("Content-Type"))

# if response.ok:
#     with open("finetuning.jpg", "wb") as file:
#         file.write(response.content)

#     print("Image generated successfully!")
#     print("Saved as: generated_image.jpg")

# else:
#     print("Request failed:")
#     print(response.text)
USE_GEMINNI=False
def check():
  if USE_GEMINNI:
    print("True")
    print(USE_GEMINNI)
  else:
    print("false")
    print(USE_GEMINNI)

check()
