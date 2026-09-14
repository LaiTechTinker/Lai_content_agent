from app.core.config import settings

X_CLIENT_ID = settings.x_client_id
X_CLIENT_SECRET = settings.x_client_secret
X_REDIRECT_URI = settings.x_redirect_uri

LINKEDIN_CLIENT_ID = settings.linkedin_client_id
LINKEDIN_CLIENT_SECRET = settings.linkedin_client_secret
LINKEDIN_REDIRECT_URI = settings.linkedin_redirect_uri
LINKEDIN_API_VERSION = settings.linkedin_api_version


def x_configured() -> bool:
    return bool(X_CLIENT_ID and X_CLIENT_SECRET and X_REDIRECT_URI)


def linkedin_configured() -> bool:
    return bool(LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET and LINKEDIN_REDIRECT_URI)