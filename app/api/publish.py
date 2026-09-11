from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.generated_content_service import get_content
from app.services.social_account_service import get_social_account
from app.services.publishing_service import (
    can_publish,
    mark_publishing,
    mark_published,
    mark_publish_failed,
    publish_content,
)

router = APIRouter(prefix="/api", tags=["publishing"])


class PublishRequest(BaseModel):
    content_id: int
    platform: Literal["X", "LinkedIn"]


@router.post("/publish")
def publish(request: PublishRequest):

    # 1. Get the content
    content = get_content(request.content_id)

    if content is None:
        raise HTTPException(
            status_code=404,
            detail="Content not found",
        )

    # 2. Make sure the content is approved
    if content["status"] != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved content can be published",
        )

    # 3. Prevent duplicate publishing
    if not can_publish(request.content_id):
        raise HTTPException(
            status_code=409,
            detail="Content has already been published or cannot be published",
        )

    # 4. Get the connected social account
    account = get_social_account(request.platform)

    if account is None:
        raise HTTPException(
            status_code=400,
            detail=f"No {request.platform} account connected",
        )

    # 5. Mark as publishing
    mark_publishing(request.content_id)

    try:
        # 6. Publish to the selected platform
        result = publish_content(
            platform=request.platform,
            content=content["content"],
            account=account,
        )

        # 7. Save successful publication
        external_post_id = (
            result.get("id")
            or result.get("external_post_id")
        )

        mark_published(
            content_id=request.content_id,
            external_post_id=external_post_id,
        )

        return {
            "success": True,
            "content_id": request.content_id,
            "platform": request.platform,
            "external_post_id": external_post_id,
        }

    except Exception as error:

        mark_publish_failed(
            content_id=request.content_id,
            error=str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=f"Publishing failed: {str(error)}",
        )