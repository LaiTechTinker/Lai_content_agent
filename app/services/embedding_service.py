import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings


embeddings = GoogleGenerativeAIEmbeddings(
    model=settings.google_embedding_model,
    google_api_key=settings.require_google_api_key(),
)


def embed_text(text: str) -> list[float]:
    return embeddings.embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    return embeddings.embed_documents(texts)