from app.core.social_config import LINKEDIN_API_VERSION
from app.services.x_service import publish_to_x
from app.services.linkedin_service import publish_to_linkedin


def publish_content(
    platform: str,
    content: str,
    account: dict,
) -> dict:
    if platform == "X":
        return publish_to_x(
            text=content,
            access_token=account["access_token"],
        )

    if platform == "LinkedIn":
        linkedin_version = account.get("linkedin_version", LINKEDIN_API_VERSION)
        return publish_to_linkedin(
            text=content,
            access_token=account["access_token"],
            author_urn=account["account_id"],
            linkedin_version=linkedin_version,
        )

    raise ValueError(f"Unsupported platform: {platform}")