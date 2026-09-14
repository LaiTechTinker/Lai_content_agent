from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

llm = ChatGoogleGenerativeAI(
	model=settings.google_model,
	temperature=0.7,
	google_api_key=settings.require_google_api_key(),
)