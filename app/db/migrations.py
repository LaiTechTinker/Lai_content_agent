import sqlite3

DB_PATH = "content_engine.db"


def run_migrations():
    connection = sqlite3.connect(DB_PATH)

    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(generated_content)"
        ).fetchall()
    }

    migrations = {
        "published_at": """
            ALTER TABLE generated_content
            ADD COLUMN published_at TIMESTAMP
        """,
        "publish_status": """
            ALTER TABLE generated_content
            ADD COLUMN publish_status TEXT DEFAULT 'not_published'
        """,
        "external_post_id": """
            ALTER TABLE generated_content
            ADD COLUMN external_post_id TEXT
        """,
        "publish_error": """
            ALTER TABLE generated_content
            ADD COLUMN publish_error TEXT
        """,
    }

    for column, sql in migrations.items():
        if column not in columns:
            connection.execute(sql)
            print(f"Added column: {column}")

    connection.commit()
    connection.close()


if __name__ == "__main__":
    run_migrations()