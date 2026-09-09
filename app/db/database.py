import sqlite3
db_path="content.db"

def get_connection(db_path=db_path):
    connection =sqlite3.connect(db_path)
    connection.row_factory=sqlite3.Row
    return connection

def init_db():
    connection = get_connection()
    connection.execute("""
    CREATE TABLE IF NOT EXISTS content_ideas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        title TEXT NOT NULL,
        angle TEXT,
        platform TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        
    )
""")
    connection.commit()
    connection.close()