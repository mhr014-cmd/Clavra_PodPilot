from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.provider import generate_ai_response

router = APIRouter(prefix="/ai", tags=["AI"])


class AIRequest(BaseModel):
    prompt: str


@router.post("/ask")
async def ask_ai(data: AIRequest):

    response = await generate_ai_response(data.prompt)

    return {
        "response": response
    }