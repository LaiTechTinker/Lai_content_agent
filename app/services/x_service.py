import os

import requests

from dotenv import load_dotenv

load_dotenv()


X_POST_URL = "https://api.x.com/2/tweets"


def publish_to_x(
    text: str,
    access_token: str,
) -> dict:

    response = requests.post(
        X_POST_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "text": text,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"X publishing failed: "
            f"{response.status_code} "
            f"{response.text}"
        )

    return response.json()