import asyncio
from langchain_ollama import ChatOllama
from app.config import settings

llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL
)


async def ask_ollama(prompt: str) -> str:
    """Run Ollama in a thread pool so it doesn't block the event loop."""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, llm.invoke, prompt)
    return response.content