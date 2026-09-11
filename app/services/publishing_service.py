from app.services.x_service import publish_to_x
from app.services.linkedin_service import (
    publish_to_linkedin,
)


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
        return publish_to_linkedin(
            text=content,
            access_token=account["access_token"],
            author_urn=account["account_id"],
            linkedin_version=account[
                "linkedin_version"
            ],
        )

    raise ValueError(
        f"Unsupported platform: {platform}"
    )