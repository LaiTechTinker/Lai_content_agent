import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from app.services.social_account_service import (
    create_oauth_state_record,
    consume_oauth_state,
    save_social_account,
)

load_dotenv()

SUPPORTED_PLATFORMS = {"X", "LinkedIn"}


def normalize_platform(platform: str) -> str:
    aliases = {"x": "X", "twitter": "X", "linkedin": "LinkedIn"}
    try:
        return aliases[platform.lower()]
    except KeyError as exc:
        raise ValueError("Unsupported platform. Use X or LinkedIn.") from exc


def _pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_connect_url(platform: str):
    platform = normalize_platform(platform)
    if platform == "LinkedIn":
        client_id = os.getenv("LINKEDIN_CLIENT_ID")
        redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
        if not client_id or not redirect_uri:
            raise RuntimeError("LinkedIn OAuth is not configured.")
        state = create_oauth_state_record(platform)
        query = urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "openid profile w_member_social",
        })
        return f"https://www.linkedin.com/oauth/v2/authorization?{query}"

    client_id = os.getenv("X_CLIENT_ID")
    redirect_uri = os.getenv("X_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise RuntimeError("X OAuth is not configured.")
    verifier, challenge = _pkce_pair()
    state = create_oauth_state_record(platform, verifier)
    query = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return f"https://twitter.com/i/oauth2/authorize?{query}"


def complete_callback(platform: str, code: str, state: str):
    platform = normalize_platform(platform)
    state_record = consume_oauth_state(state)
    if not state_record or state_record["platform"] != platform:
        raise ValueError("Invalid or expired OAuth state.")

    if platform == "LinkedIn":
        token_response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": os.getenv("LINKEDIN_REDIRECT_URI"),
                "client_id": os.getenv("LINKEDIN_CLIENT_ID"),
                "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET"),
            },
            timeout=30,
        )
        token_response.raise_for_status()
        token = token_response.json()
        profile = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            timeout=30,
        )
        profile.raise_for_status()
        user = profile.json()
        account_id = user.get("sub")
        account_name = user.get("name") or user.get("given_name") or account_id
    else:
        token_response = requests.post(
            "https://api.x.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": os.getenv("X_CLIENT_ID"),
                "redirect_uri": os.getenv("X_REDIRECT_URI"),
                "code_verifier": state_record.get("code_verifier"),
            },
            timeout=30,
        )
        token_response.raise_for_status()
        token = token_response.json()
        profile = requests.get(
            "https://api.x.com/2/users/me",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            timeout=30,
        )
        profile.raise_for_status()
        user = profile.json().get("data", {})
        account_id = user.get("id")
        account_name = user.get("name") or user.get("username") or account_id

    if not account_id or not token.get("access_token"):
        raise RuntimeError("OAuth provider returned incomplete account data.")
    save_social_account(
        platform=platform,
        account_id=account_id,
        account_name=account_name,
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_expires_at=None,
    )
    return {"platform": platform, "account_name": account_name}
