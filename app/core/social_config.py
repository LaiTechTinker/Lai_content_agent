import os

from dotenv import load_dotenv

load_dotenv()


X_CLIENT_ID = os.getenv("X_CLIENT_ID")
X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET")
X_REDIRECT_URI = os.getenv("X_REDIRECT_URI")

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv(
    "LINKEDIN_CLIENT_SECRET"
)
LINKEDIN_REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI"
)