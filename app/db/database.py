import json
import sqlite3

DB_PATH = "content.db"


def _initialize_schema(connection: sqlite3.Connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS content_ideas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            title TEXT NOT NULL,
            angle TEXT,
            platform TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS generated_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL,
            content TEXT NOT NULL,
            quality_score INTEGER,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            published_at TIMESTAMP,
            publish_status TEXT DEFAULT 'not_published',
            external_post_id TEXT,
            publish_error TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS content_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            media_type TEXT NOT NULL,
            media_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES generated_content(id)
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS social_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL UNIQUE,
            account_id TEXT,
            account_name TEXT,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            token_expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute("PRAGMA foreign_keys = ON")

    migration_checks = {
        "generated_content": [
            ("approved_at", "ALTER TABLE generated_content ADD COLUMN approved_at TIMESTAMP"),
            ("published_at", "ALTER TABLE generated_content ADD COLUMN published_at TIMESTAMP"),
            ("publish_status", "ALTER TABLE generated_content ADD COLUMN publish_status TEXT DEFAULT 'not_published'"),
            ("external_post_id", "ALTER TABLE generated_content ADD COLUMN external_post_id TEXT"),
            ("publish_error", "ALTER TABLE generated_content ADD COLUMN publish_error TEXT"),
        ]
    }

    for table_name, columns in migration_checks.items():
        existing_columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, ddl in columns:
            if column_name not in existing_columns:
                connection.execute(ddl)

    connection.commit()


def get_connection(db_path=DB_PATH):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    table_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'generated_content'"
    ).fetchone()

    if table_exists is None:
        _initialize_schema(connection)
    else:
        existing_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(generated_content)").fetchall()
        }
        if "approved_at" not in existing_columns:
            _initialize_schema(connection)

    return connection


def init_db():
    connection = sqlite3.connect(DB_PATH)
    try:
        _initialize_schema(connection)
    finally:
        connection.close()


def run_migrations():
    connection = sqlite3.connect(DB_PATH)
    try:
        _initialize_schema(connection)
    finally:
        connection.close()


def save_content_ideas(topic: str, platform: str, angle: str, title: str):
    connection = get_connection()
    cursor = connection.execute(
        """
        INSERT INTO content_ideas(topic, platform, angle, title)
        VALUES(?,?,?,?)
        """,
        (topic, platform, angle, title),
    )
    connection.commit()
    idea_id = cursor.lastrowid
    connection.close()
    return idea_id


def create_document(filename: str, file_type: str):
    connection = get_connection()
    cursor = connection.execute(
        """
        INSERT INTO documents (filename, file_type)
        VALUES (?, ?)
        """,
        (filename, file_type),
    )
    connection.commit()
    document_id = cursor.lastrowid
    connection.close()
    return document_id


def save_document_chunk(document_id: int, chunk_text: str, embedding: list[float]):
    connection = get_connection()
    connection.execute(
        """
        INSERT INTO document_chunks (document_id, chunk_text, embedding)
        VALUES (?, ?, ?)
        """,
        (document_id, chunk_text, json.dumps(embedding)),
    )
    connection.commit()
    connection.close()


def list_knowledge():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT id, filename, file_type, created_at
        FROM documents
        ORDER BY created_at DESC
        """
    ).fetchall()
    connection.close()
    return {"documents": [dict(row) for row in rows]}


# async def get_idea_by_id(idea_id:int):
#     connection=get_connection()
#     cursor=connection.execute("""
#     SELECT * FROM content_ideas WHERE id=?
#     """,(idea_id,))
#     idea=cursor.fetchone()
#     connection.close()
#     return idea