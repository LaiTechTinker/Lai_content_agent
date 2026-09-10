from pathlib import Path

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


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