from app.services.publishing_service import (
    publish_content,
)

from app.services.publication_service import (
    mark_publishing,
    mark_published,
    mark_publish_failed,
)


def publish_content_node(state):

    content_id = state.get("content_id")
    platform = state.get("platform")
    content = state.get("final_content")

    if not content_id:
        raise ValueError(
            "Missing content ID."
        )

    if not content:
        raise ValueError(
            "Missing final content."
        )

    mark_publishing(content_id)

    try:

        # Replace this with your real account lookup.
        account = state["social_account"]

        result = publish_content(
            platform=platform,
            content=content,
            account=account,
        )

        external_post_id = (
            result.get("post_id")
            or result.get("data", {}).get("id")
        )

        mark_published(
            content_id=content_id,
            external_post_id=external_post_id,
        )

        return {
            "publish_status": "published",
            "external_post_id": external_post_id,
        }

    except Exception as exc:

        mark_publish_failed(
            content_id=content_id,
            error=str(exc),
        )

        raise