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

    connection.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id)
                REFERENCES documents(id)
        )
    """)
    connection.commit()
    connection.close()

# this code block saved ideas to the database

def save_content_ideas(topic:str,platform:str,angle:str,title:str):

    connection = get_connection()
    cursor=connection.execute("""
    INSERT INTO content_ideas(topic,platform,angle,title)
    VALUES(?,?,?,?)
    """,(topic,platform,angle,title))
    connection.commit()
    idea_id=cursor.lastrowid
    connection.close()
    return idea_id

# async def get_idea_by_id(idea_id:int):
#     connection=get_connection()
#     cursor=connection.execute("""
#     SELECT * FROM content_ideas WHERE id=?
#     """,(idea_id,))
#     idea=cursor.fetchone()
#     connection.close()
#     return idea