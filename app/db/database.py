import json
import re
import sqlite3

from app.core.config import settings
from app.db.base import Base
from sqlalchemy import create_engine, text

DB_PATH = settings.database_path


def _is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite:")


def _configured_sqlite_path() -> str:
    if settings.database_url == "sqlite:///:memory:":
        return ":memory:"
    if settings.database_url.startswith("sqlite:///"):
        return settings.database_url.removeprefix("sqlite:///")
    return DB_PATH


class _CompatResult:
    def __init__(self, result):
        self._result = result
        self.rowcount = result.rowcount
        self.lastrowid = getattr(result.cursor, "lastrowid", None)

    def fetchone(self):
        row = self._result.fetchone()
        return _CompatRow(row) if row is not None else None

    def fetchall(self):
        return [_CompatRow(row) for row in self._result.fetchall()]


class _CompatRow(dict):
    def __init__(self, row):
        super().__init__(row._mapping)
        self._values = tuple(row)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class _PostgresConnection:
    """Small DB-API-shaped adapter for legacy service queries."""

    def __init__(self, engine):
        self._connection = engine.connect()
        self._lastrowid = None

    def cursor(self):
        return self

    def execute(self, sql, parameters=()):
        bind_parameters = {}
        parameter_index = 0

        def replace_parameter(_match):
            nonlocal parameter_index
            name = f"p{parameter_index}"
            bind_parameters[name] = parameters[parameter_index]
            parameter_index += 1
            return f":{name}"

        statement = re.sub(r"\?", replace_parameter, sql)
        result = self._connection.execute(text(statement), bind_parameters)
        wrapped = _CompatResult(result)
        self._lastrowid = wrapped.lastrowid
        if self._lastrowid is None and statement.lstrip().upper().startswith("INSERT"):
            self._lastrowid = self._connection.execute(text("SELECT lastval()"), {}).scalar()
        wrapped.lastrowid = self._lastrowid
        return wrapped

    @property
    def lastrowid(self):
        return self._lastrowid

    def commit(self):
        self._connection.commit()

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _ensure_phase2_schema(connection: sqlite3.Connection):
    """Add Phase 2 structures without replacing existing SQLite data."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            name TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS content_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            user_id INTEGER,
            version_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            evaluation TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(content_id, version_number),
            FOREIGN KEY (content_id) REFERENCES generated_content(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            thread_id TEXT NOT NULL UNIQUE,
            status TEXT,
            current_stage TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            revoked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    ownership_tables = {
        "content_ideas": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
        "generated_content": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
        "documents": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
        "social_accounts": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
        "oauth_states": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
        "content_publications": "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
    }
    for table_name in ownership_tables:
        columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if "user_id" not in columns:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER")

    social_unique_indexes = connection.execute(
        "PRAGMA index_list(social_accounts)"
    ).fetchall()
    has_platform_only_unique = any(
        index[2]
        and [row[2] for row in connection.execute(f"PRAGMA index_info({index[1]})").fetchall()] == ["platform"]
        for index in social_unique_indexes
    )
    if has_platform_only_unique:
        connection.execute("ALTER TABLE social_accounts RENAME TO social_accounts_legacy")
        connection.execute(
            """
            CREATE TABLE social_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT NOT NULL,
                account_id TEXT,
                account_name TEXT,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                token_expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO social_accounts
            (id, user_id, platform, account_id, account_name, access_token,
             refresh_token, token_expires_at, created_at, updated_at, connected_at)
            SELECT id, user_id, platform, account_id, account_name, access_token,
                   refresh_token, token_expires_at, created_at, updated_at, connected_at
            FROM social_accounts_legacy
            """
        )
        connection.execute("DROP TABLE social_accounts_legacy")

    indexes = {
        "ix_content_ideas_user_created": "content_ideas(user_id, created_at)",
        "ix_generated_content_user_created": "generated_content(user_id, created_at)",
        "ix_documents_user_created": "documents(user_id, created_at)",
        "ix_content_publications_user_created": "content_publications(user_id, created_at)",
        "ix_workflow_sessions_user_updated": "workflow_sessions(user_id, updated_at)",
    }
    for index_name, columns in indexes.items():
        connection.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {columns}")


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
            publish_error TEXT,
            thread_id TEXT,
            prompt TEXT,
            selected_idea TEXT,
            research_required INTEGER,
            research_query TEXT,
            research_results TEXT,
            evaluation TEXT,
            quality_feedback TEXT,
            refinement_count INTEGER DEFAULT 0,
            review_feedback TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
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
            status TEXT DEFAULT 'generated',
            attempt_count INTEGER DEFAULT 0,
            error TEXT,
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
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            code_verifier TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS content_publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            account_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            platform_post_id TEXT,
            platform_post_url TEXT,
            error_message TEXT,
            media_ids TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES generated_content(id)
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
            ("thread_id", "ALTER TABLE generated_content ADD COLUMN thread_id TEXT"),
            ("prompt", "ALTER TABLE generated_content ADD COLUMN prompt TEXT"),
            ("selected_idea", "ALTER TABLE generated_content ADD COLUMN selected_idea TEXT"),
            ("research_required", "ALTER TABLE generated_content ADD COLUMN research_required INTEGER"),
            ("research_query", "ALTER TABLE generated_content ADD COLUMN research_query TEXT"),
            ("research_results", "ALTER TABLE generated_content ADD COLUMN research_results TEXT"),
            ("evaluation", "ALTER TABLE generated_content ADD COLUMN evaluation TEXT"),
            ("quality_feedback", "ALTER TABLE generated_content ADD COLUMN quality_feedback TEXT"),
            ("refinement_count", "ALTER TABLE generated_content ADD COLUMN refinement_count INTEGER DEFAULT 0"),
            ("review_feedback", "ALTER TABLE generated_content ADD COLUMN review_feedback TEXT"),
            ("updated_at", "ALTER TABLE generated_content ADD COLUMN updated_at TIMESTAMP"),
            ("completed_at", "ALTER TABLE generated_content ADD COLUMN completed_at TIMESTAMP"),
        ],
        "social_accounts": [
            ("connected_at", "ALTER TABLE social_accounts ADD COLUMN connected_at TIMESTAMP"),
        ],
        "content_media": [
            ("status", "ALTER TABLE content_media ADD COLUMN status TEXT DEFAULT 'generated'"),
            ("attempt_count", "ALTER TABLE content_media ADD COLUMN attempt_count INTEGER DEFAULT 0"),
            ("error", "ALTER TABLE content_media ADD COLUMN error TEXT"),
        ],
    }

    for table_name, columns in migration_checks.items():
        existing_columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, ddl in columns:
            if column_name not in existing_columns:
                connection.execute(ddl)

    _ensure_phase2_schema(connection)

    connection.commit()


def get_connection(db_path=DB_PATH):
    if not _is_sqlite_url(settings.database_url) and db_path == DB_PATH:
        return _PostgresConnection(create_engine(settings.database_url, pool_pre_ping=True))
    if db_path != DB_PATH or _is_sqlite_url(settings.database_url):
        if db_path == DB_PATH:
            db_path = _configured_sqlite_path()
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
        media_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(content_media)").fetchall()
        }
        publication_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'content_publications'"
        ).fetchone()
        oauth_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'oauth_states'"
        ).fetchone()
        phase2_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        ownership_columns = {
            table_name: {
                row[1]
                for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            }
            for table_name in (
                "content_ideas",
                "generated_content",
                "documents",
                "social_accounts",
                "oauth_states",
                "content_publications",
            )
        }
        social_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(social_accounts)").fetchall()
        }
        required_content_columns = {
            "thread_id", "prompt", "selected_idea", "research_required",
            "research_query", "research_results", "evaluation", "quality_feedback",
            "refinement_count", "review_feedback", "updated_at", "completed_at",
        }
        if (
            "approved_at" not in existing_columns
            or "status" not in media_columns
            or "attempt_count" not in media_columns
            or "error" not in media_columns
            or not required_content_columns.issubset(existing_columns)
            or publication_table is None
            or oauth_table is None
            or "connected_at" not in social_columns
            or not {"users", "content_versions", "workflow_sessions", "refresh_sessions"}.issubset(phase2_tables)
            or any("user_id" not in columns for columns in ownership_columns.values())
        ):
            _initialize_schema(connection)

    return connection


def init_db():
    if _is_sqlite_url(settings.database_url):
        connection = sqlite3.connect(_configured_sqlite_path())
        try:
            _initialize_schema(connection)
        finally:
            connection.close()
        return

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def run_migrations():
    init_db()


def save_content_ideas(topic: str, platform: str, angle: str, title: str, user_id: int | None = None):
    connection = get_connection()
    cursor = connection.execute(
        """
        INSERT INTO content_ideas(user_id, topic, platform, angle, title)
        VALUES(?,?,?,?,?)
        """,
        (user_id, topic, platform, angle, title),
    )
    connection.commit()
    idea_id = cursor.lastrowid
    connection.close()
    return idea_id


def create_document(filename: str, file_type: str, user_id: int | None = None):
    connection = get_connection()
    cursor = connection.execute(
        """
        INSERT INTO documents (user_id, filename, file_type)
        VALUES (?, ?, ?)
        """,
        (user_id, filename, file_type),
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


def list_knowledge(user_id: int | None = None):
    connection = get_connection()
    rows = connection.execute(
        f"""
        SELECT id, filename, file_type, created_at
        FROM documents
        {"WHERE user_id = ?" if user_id is not None else ""}
        ORDER BY created_at DESC
        """
        , (user_id,) if user_id is not None else ()).fetchall()
    connection.close()
    return {"documents": [dict(row) for row in rows]}


def create_workflow_session(thread_id: str, user_id: int):
    connection = get_connection()
    connection.execute(
        """
        INSERT INTO workflow_sessions (user_id, thread_id, status, current_stage)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(thread_id) DO UPDATE SET user_id = excluded.user_id
        """,
        (user_id, thread_id, "active", "started"),
    )
    connection.commit()
    connection.close()


def owns_workflow_session(thread_id: str, user_id: int) -> bool:
    connection = get_connection()
    row = connection.execute(
        "SELECT 1 FROM workflow_sessions WHERE thread_id = ? AND user_id = ?",
        (thread_id, user_id),
    ).fetchone()
    connection.close()
    return row is not None


def workflow_session_exists(thread_id: str) -> bool:
    connection = get_connection()
    row = connection.execute(
        "SELECT 1 FROM workflow_sessions WHERE thread_id = ?",
        (thread_id,),
    ).fetchone()
    connection.close()
    return row is not None


def get_workflow_session(thread_id: str, user_id: int):
    connection = get_connection()
    row = connection.execute(
        "SELECT * FROM workflow_sessions WHERE thread_id = ? AND user_id = ?",
        (thread_id, user_id),
    ).fetchone()
    connection.close()
    return dict(row) if row else None


def update_workflow_session(thread_id: str, user_id: int, status: str, current_stage: str):
    connection = get_connection()
    connection.execute(
        """
        UPDATE workflow_sessions
        SET status = ?, current_stage = ?, updated_at = CURRENT_TIMESTAMP
        WHERE thread_id = ? AND user_id = ?
        """,
        (status, current_stage, thread_id, user_id),
    )
    connection.commit()
    connection.close()


def get_content_version_summary(content_id: int, user_id: int) -> dict:
    connection = get_connection()
    row = connection.execute(
        """
        SELECT COUNT(*) AS version_count, MAX(version_number) AS latest_version
        FROM content_versions
        WHERE content_id = ? AND user_id = ?
        """,
        (content_id, user_id),
    ).fetchone()
    connection.close()
    return {
        "version_count": row["version_count"] if row else 0,
        "latest_version": row["latest_version"] if row else None,
    }


def list_content_versions(content_id: int, user_id: int) -> list[dict]:
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT version_number, content, evaluation, metadata, created_at
        FROM content_versions
        WHERE content_id = ? AND user_id = ?
        ORDER BY version_number ASC
        """,
        (content_id, user_id),
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


# async def get_idea_by_id(idea_id:int):
#     connection=get_connection()
#     cursor=connection.execute("""
#     SELECT * FROM content_ideas WHERE id=?
#     """,(idea_id,))
#     idea=cursor.fetchone()
#     connection.close()
#     return idea