from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.generated_content_service import get_content
from app.services.media_service import get_media
from app.services.oauth_service import (
    build_connect_url,
    complete_callback,
    normalize_platform,
)
from app.services.publication_service import (
    create_publication,
    get_publication,
    has_published_attempt,
    list_publications,
    mark_publication_failed,
    mark_publication_published,
    mark_publication_publishing,
)
from app.services.publishing_service import publish_content
from app.services.social_account_service import (
    disconnect_social_account,
    get_social_account,
    list_connected_accounts,
)

router = APIRouter(tags=["publishing"])


class PublishRequest(BaseModel):
    platform: Literal["X", "LinkedIn", "x", "linkedin"]
    media_ids: list[int] = Field(default_factory=list)
    republish: bool = False


def _post_details(platform: str, result: dict):
    post_id = result.get("post_id") or result.get("id") or result.get("data", {}).get("id")
    if not post_id:
        return None, None
    if platform == "X":
        return post_id, f"https://x.com/i/web/status/{post_id}"
    return post_id, f"https://www.linkedin.com/feed/update/{post_id}"


def _validate_media(content_id: int, media_ids: list[int]):
    if not media_ids:
        return []
    accepted = []
    for media_id in media_ids:
        media = get_media(media_id)
        if (
            not media
            or media["content_id"] != content_id
            or media["media_type"] != "image"
            or media["status"] != "accepted"
            or not media.get("media_url")
        ):
            raise HTTPException(status_code=400, detail=f"Media {media_id} is not an accepted image for this content.")
        accepted.append(media)
    return accepted


@router.get("/publishing/accounts")
def publishing_accounts():
    return [
        {
            "platform": account["platform"],
            "connected": True,
            "account_id": account.get("account_id"),
            "account_name": account.get("account_name"),
            "connected_at": account.get("connected_at"),
        }
        for account in list_connected_accounts()
    ]


@router.get("/publishing/{platform}/connect")
def connect_platform(platform: str):
    try:
        normalized = normalize_platform(platform)
        return {"platform": normalized, "authorization_url": build_connect_url(normalized)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/publishing/{platform}/callback")
def platform_callback(
    platform: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    if error:
        raise HTTPException(status_code=400, detail=f"Platform authorization failed: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="OAuth code and state are required.")
    try:
        return complete_callback(platform, code, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Platform authorization failed: {exc}") from exc


@router.delete("/publishing/{platform}/disconnect")
def disconnect_platform(platform: str):
    try:
        normalized = normalize_platform(platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"disconnected": disconnect_social_account(normalized), "platform": normalized}


@router.post("/content/{content_id}/publish")
def publish(content_id: int, request: PublishRequest):
    content = get_content(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    if content["status"] not in {"approved", "completed"}:
        raise HTTPException(status_code=400, detail="Only approved or completed content can be published.")
    if not content.get("final_content"):
        raise HTTPException(status_code=400, detail="Content has no final content to publish.")

    try:
        platform = normalize_platform(request.platform)
        account = get_social_account(platform)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    accepted_media = _validate_media(content_id, request.media_ids)
    if accepted_media:
        raise HTTPException(
            status_code=400,
            detail=f"{platform} image upload is not implemented; publish text without media.",
        )

    previous = has_published_attempt(content_id, platform, account.get("account_id"))
    if previous and not request.republish:
        raise HTTPException(status_code=409, detail=f"Content has already been published to {platform}.")

    publication_id = create_publication(content_id, platform, account.get("account_id"), request.media_ids)
    mark_publication_publishing(publication_id)
    try:
        result = publish_content(
            platform=platform,
            content=content["final_content"],
            account=account,
        )
        post_id, post_url = _post_details(platform, result)
        mark_publication_published(publication_id, post_id, post_url)
        return get_publication(publication_id)
    except Exception as exc:
        mark_publication_failed(publication_id, str(exc))
        raise HTTPException(status_code=502, detail={
            "message": "Publishing failed",
            "publication_id": publication_id,
        }) from exc


@router.get("/content/{content_id}/publications")
def content_publications(content_id: int):
    if get_content(content_id) is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"items": list_publications(content_id)}


@router.get("/publications/{publication_id}")
def publication_details(publication_id: int):
    publication = get_publication(publication_id)
    if publication is None:
        raise HTTPException(status_code=404, detail="Publication not found")
    return publication


@router.post("/publications/{publication_id}/retry")
def retry_publication(publication_id: int):
    previous = get_publication(publication_id)
    if previous is None:
        raise HTTPException(status_code=404, detail="Publication not found")
    if previous["status"] not in {"failed", "cancelled"}:
        raise HTTPException(status_code=400, detail="Only failed or cancelled publications can be retried.")
    return publish(previous["content_id"], PublishRequest(platform=previous["platform"], media_ids=previous["media_ids"], republish=True))
