import sqlite3

import pytest

from app.db.database import get_connection
from app.services import generated_content_service


def test_users_have_unique_email_and_owned_content(tmp_path, monkeypatch):
    db_path = str(tmp_path / "phase2.db")
    monkeypatch.setattr(generated_content_service, "get_connection", lambda: get_connection(db_path))

    with get_connection(db_path) as connection:
        user_a = connection.execute(
            "INSERT INTO users (email, name) VALUES (?, ?)",
            ("a@example.com", "User A"),
        ).lastrowid
        user_b = connection.execute(
            "INSERT INTO users (email, name) VALUES (?, ?)",
            ("b@example.com", "User B"),
        ).lastrowid
        connection.commit()

    content_a = generated_content_service.save_generated_content(
        user_id=user_a,
        idea_id=None,
        platform="X",
        content_type="technical",
        content="A",
        quality_score=8,
    )
    content_b = generated_content_service.save_generated_content(
        user_id=user_b,
        idea_id=None,
        platform="X",
        content_type="technical",
        content="B",
        quality_score=8,
    )

    with get_connection(db_path) as connection:
        owners = connection.execute(
            "SELECT id, user_id FROM generated_content ORDER BY id"
        ).fetchall()
        assert [(row[0], row[1]) for row in owners] == [
            (content_a, user_a),
            (content_b, user_b),
        ]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO users (email) VALUES (?)", ("a@example.com",))


def test_content_versions_preserve_full_history(tmp_path, monkeypatch):
    db_path = str(tmp_path / "versions.db")
    monkeypatch.setattr(generated_content_service, "get_connection", lambda: get_connection(db_path))

    content_id = generated_content_service.save_generated_content(
        user_id=None,
        idea_id=None,
        platform="LinkedIn",
        content_type="technical",
        content="Original",
        quality_score=8,
    )
    generated_content_service.update_content_after_review(content_id, "Refinement 1", "review")
    generated_content_service.update_content_after_review(content_id, "Refinement 2", "review")

    with get_connection(db_path) as connection:
        versions = connection.execute(
            "SELECT version_number, content FROM content_versions WHERE content_id = ? ORDER BY version_number",
            (content_id,),
        ).fetchall()
        assert [(row[0], row[1]) for row in versions] == [
            (1, "Original"),
            (2, "Refinement 1"),
            (3, "Refinement 2"),
        ]


def test_phase2_schema_contains_expected_ownership_tables(tmp_path):
    with get_connection(str(tmp_path / "schema.db")) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "users",
            "content_ideas",
            "generated_content",
            "content_versions",
            "documents",
            "document_chunks",
            "content_media",
            "social_accounts",
            "oauth_states",
            "content_publications",
            "workflow_sessions",
        } <= tables


def test_owned_relationships_and_per_user_social_accounts(tmp_path):
    with get_connection(str(tmp_path / "relationships.db")) as connection:
        user_a = connection.execute("INSERT INTO users (email) VALUES (?)", ("a@example.com",)).lastrowid
        user_b = connection.execute("INSERT INTO users (email) VALUES (?)", ("b@example.com",)).lastrowid
        idea_id = connection.execute(
            "INSERT INTO content_ideas (user_id, topic, title) VALUES (?, ?, ?)",
            (user_a, "topic", "idea"),
        ).lastrowid
        content_id = connection.execute(
            "INSERT INTO generated_content (user_id, idea_id, platform, content_type, content) VALUES (?, ?, ?, ?, ?)",
            (user_a, idea_id, "X", "technical", "draft"),
        ).lastrowid
        document_id = connection.execute(
            "INSERT INTO documents (user_id, filename) VALUES (?, ?)",
            (user_a, "notes.md"),
        ).lastrowid
        connection.execute(
            "INSERT INTO document_chunks (document_id, chunk_text, embedding) VALUES (?, ?, ?)",
            (document_id, "chunk", "[]"),
        )
        connection.execute(
            "INSERT INTO content_media (content_id, media_type) VALUES (?, ?)",
            (content_id, "image"),
        )
        connection.execute(
            "INSERT INTO content_publications (user_id, content_id, platform) VALUES (?, ?, ?)",
            (user_a, content_id, "X"),
        )
        connection.execute(
            "INSERT INTO social_accounts (user_id, platform, access_token) VALUES (?, ?, ?)",
            (user_a, "X", "token-a"),
        )
        connection.execute(
            "INSERT INTO social_accounts (user_id, platform, access_token) VALUES (?, ?, ?)",
            (user_b, "X", "token-b"),
        )
        connection.commit()

        assert connection.execute("SELECT user_id FROM content_ideas").fetchone()[0] == user_a
        assert connection.execute("SELECT document_id FROM document_chunks").fetchone()[0] == document_id
        assert connection.execute("SELECT content_id FROM content_media").fetchone()[0] == content_id
        assert connection.execute("SELECT COUNT(*) FROM social_accounts WHERE platform = 'X'").fetchone()[0] == 2