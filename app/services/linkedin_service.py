import requests


LINKEDIN_POST_URL = (
    "https://api.linkedin.com/rest/posts"
)


def publish_to_linkedin(
    text: str,
    access_token: str,
    author_urn: str,
    linkedin_version: str,
) -> dict:

    payload = {
        "author": author_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    response = requests.post(
        LINKEDIN_POST_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": linkedin_version,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"LinkedIn publishing failed: "
            f"{response.status_code} "
            f"{response.text}"
        )

    return {
        "response": response.json()
        if response.content
        else {},
        "post_id": response.headers.get(
            "x-restli-id"
        ),
    }