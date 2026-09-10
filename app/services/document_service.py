from pathlib import Path

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.db.database import (
    create_document,
    save_document_chunk,
)

from app.services.embedding_service import (
    embed_documents,
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
)


def extract_text(file_path: str) -> str:

    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(file_path)

        pages = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

        return "\n".join(pages)

    if path.suffix.lower() in [".txt", ".md"]:
        return path.read_text(
            encoding="utf-8"
        )

    raise ValueError(
        f"Unsupported file type: {path.suffix}"
    )


def chunk_text(text: str) -> list[str]:

    return splitter.split_text(text)


def ingest_document(file_path: str):

    from pathlib import Path

    path = Path(file_path)

    text = extract_text(file_path)

    if not text.strip():
        raise ValueError(
            "Document contains no readable text."
        )

    chunks = chunk_text(text)

    document_id = create_document(
        filename=path.name,
        file_type=path.suffix.lower(),
    )

    embeddings = embed_documents(chunks)

    for chunk, embedding in zip(
        chunks,
        embeddings,
    ):
        save_document_chunk(
            document_id=document_id,
            chunk_text=chunk,
            embedding=embedding,
        )

    return {
        "document_id": document_id,
        "filename": path.name,
        "chunks": len(chunks),
    }