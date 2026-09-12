from types import SimpleNamespace

from app.graphs.content_nodes import (
    content_quality_router,
    decide_research,
    generate_content_node,
    human_select_idea_node,
)
from app.graphs.human_reveiw import (
    finalize_human_review_node,
    human_review_node,
    review_action_router,
)


def test_selected_idea_is_used_for_generation(monkeypatch):
    selected = SimpleNamespace(
        title="Selected title",
        angle="Selected angle",
        reason="Selected reason",
        model_dump=lambda: {
            "title": "Selected title",
            "angle": "Selected angle",
            "reason": "Selected reason",
        },
    )
    other = SimpleNamespace(
        title="Other title",
        angle="Other angle",
        reason="Other reason",
        model_dump=lambda: {"title": "Other title"},
    )
    captured = {}

    def fake_generate_content(**kwargs):
        captured["idea"] = kwargs["idea"]
        return "generated from selected idea"

    monkeypatch.setattr(
        "app.graphs.content_nodes.generate_content",
        fake_generate_content,
    )

    result = generate_content_node(
        {
            "topic": "topic",
            "platform": "X",
            "content_type": "technical",
            "ideas": [other, selected],
            "selected_idea": selected,
        }
    )

    assert result["generated_content"] == "generated from selected idea"
    assert captured["idea"]["title"] == "Selected title"


def test_idea_selection_requires_one_saved_id(monkeypatch):
    monkeypatch.setattr(
        "app.graphs.content_nodes.interrupt",
        lambda payload: {"selected_idea_id": 12},
    )
    idea = SimpleNamespace(model_dump=lambda: {"title": "A"})

    result = human_select_idea_node(
        {"ideas": [idea], "saved_ids": [12]}
    )

    assert result["selected_idea_id"] == 12
    assert result["selected_idea"] is idea


def test_review_rejection_routes_to_rejection_terminal():
    assert review_action_router({"human_action": "reject"}) == "reject"
    assert review_action_router({"human_action": "approve"}) == "approve"


def test_rejection_preserves_feedback(monkeypatch):
    monkeypatch.setattr(
        "app.graphs.human_reveiw.interrupt",
        lambda payload: {"action": "reject", "feedback": "Wrong angle"},
    )

    result = human_review_node({"content_id": 4, "generated_content": "draft"})

    assert result["approval_status"] == "rejected"
    assert result["human_feedback"] == "Wrong angle"


def test_edit_becomes_final_content():
    result = finalize_human_review_node(
        {
            "human_action": "edit",
            "edited_content": "edited final",
            "generated_content": "original draft",
        }
    )

    assert result["final_content"] == "edited final"


def test_research_decision_uses_content_type():
    required = decide_research(
        {"topic": "latest agents", "content_type": "ai_news"}
    )
    skipped = decide_research(
        {"topic": "my build", "content_type": "build_in_public"}
    )

    assert required["research_required"] is True
    assert skipped["research_required"] is False


def test_refinement_router_has_hard_limit():
    assert content_quality_router(
        {
            "quality_score": 3,
            "evaluation": {"should_refine": True},
            "refinement_count": 0,
        }
    ) == "refine"
    assert content_quality_router(
        {
            "quality_score": 3,
            "evaluation": {"should_refine": True},
            "refinement_count": 2,
        }
    ) == "approved"