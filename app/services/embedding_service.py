import os

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings


load_dotenv()


embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-2"
)


def embed_text(text: str) -> list[float]:
    return embeddings.embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    return embeddings.embed_documents(texts)