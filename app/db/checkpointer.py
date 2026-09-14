import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from app.core.config import settings


connection = sqlite3.connect(
    settings.checkpoint_path,
    check_same_thread=False,
)

checkpointer = SqliteSaver(connection)