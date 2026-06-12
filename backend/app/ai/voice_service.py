"""Voice Service — Clavra ProdPilot™ — Whisper STT + OpenAI TTS"""
import io
from app.config import settings


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """Convert audio bytes to text using Whisper API."""
    if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.startswith("sk-"):
        return {"transcript": "", "error": "OpenAI API key required for voice"}

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language=None,  # auto-detect (supports Bengali)
    )
    return {"transcript": response.text, "error": None}


async def text_to_speech(text: str, voice: str = None) -> bytes:
    """Convert text to MP3 audio bytes using OpenAI TTS."""
    if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.startswith("sk-"):
        return b""

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.audio.speech.create(
        model="tts-1",
        voice=voice or settings.TTS_VOICE,
        input=text[:4096],  # TTS limit
    )
    return response.content


async def voice_chat(
    audio_bytes: bytes,
    user_id: int,
    org_id: int,
    db,
) -> dict:
    """Full voice pipeline: audio → transcript → AI pipeline → TTS → return all."""
    # Step 1: Transcribe
    transcription = await transcribe_audio(audio_bytes)
    if transcription.get("error"):
        return {"error": transcription["error"]}

    transcript = transcription["transcript"]
    if not transcript.strip():
        return {"error": "Could not transcribe audio. Please speak clearly."}

    # Step 2: Run through AI pipeline
    from app.ai.intent_engine import detect_intent
    from app.ai.intent_router import route_intent

    intent_result = await detect_intent(transcript)
    route_result  = await route_intent(intent_result, transcript, user_id, org_id, db)

    # Step 3: TTS
    audio_response = await text_to_speech(route_result.response)

    return {
        "transcript": transcript,
        "ai_response": route_result.response,
        "intent": route_result.intent,
        "confidence": route_result.confidence,
        "action_type": route_result.action_type,
        "audio_bytes": audio_response,
    }
