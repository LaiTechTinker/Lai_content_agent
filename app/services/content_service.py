from app.db.database import save_content_idea


def save_ideas(topic: str, ideas: list):

    saved_ids = []

    for idea in ideas:

        idea_id = save_content_idea(
            topic=topic,
            title=idea.title,
            angle=idea.angle,
            platform=idea.platform,
        )

        saved_ids.append(idea_id)

    return saved_ids