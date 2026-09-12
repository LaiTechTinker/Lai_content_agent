from app.core.social_config import LINKEDIN_API_VERSION
from app.services.x_service import publish_to_x
from app.services.linkedin_service import publish_to_linkedin


class Publisher:
    platform = ""

    def publish(self, content: str, account: dict, media=None) -> dict:
        raise NotImplementedError


class XPublisher(Publisher):
    platform = "X"

    def publish(self, content: str, account: dict, media=None) -> dict:
        if media:
            raise ValueError("Image publishing is not implemented for X yet.")
        return publish_to_x(text=content, access_token=account["access_token"])


class LinkedInPublisher(Publisher):
    platform = "LinkedIn"

    def publish(self, content: str, account: dict, media=None) -> dict:
        if media:
            raise ValueError("LinkedIn media upload is not implemented yet.")
        return publish_to_linkedin(
            text=content,
            access_token=account["access_token"],
            author_urn=account["account_id"],
            linkedin_version=account.get("linkedin_version", LINKEDIN_API_VERSION),
        )


PUBLISHERS = {
    "X": XPublisher(),
    "LinkedIn": LinkedInPublisher(),
}


def get_publisher(platform: str) -> Publisher:
    try:
        return PUBLISHERS[platform]
    except KeyError as exc:
        raise ValueError(f"Unsupported platform: {platform}") from exc


def publish_content(
    platform: str,
    content: str,
    account: dict,
) -> dict:
    return get_publisher(platform).publish(content, account)