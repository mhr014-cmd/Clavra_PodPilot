from app.config import settings
from app.ai.ollama_service import ask_ollama


async def generate_ai_response(prompt: str):
    if settings.AI_PROVIDER == "ollama":
        return await ask_ollama(prompt)

    return "No AI provider configured."