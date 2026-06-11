"""
AI Chat Routes — Clavra ProdPilot™
Main chat endpoint + WebSocket streaming + voice chat.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json, asyncio

from app.dependencies import get_db, get_current_user
from app.schemas.auth import UserRead
from app.schemas.ai_schema import ChatRequest, ChatResponse
from app.models.ai_chat import AIConversation, AIMessage
from app.ai.intent_engine import detect_intent
from app.ai.intent_router import route_intent

router = APIRouter(prefix="/ai", tags=["AI Copilot"])

PLACEHOLDER_KEYS = {"sk-your-openai-key-here", "sk-xxxx", "sk-placeholder", ""}


# ── GET /ai/health ────────────────────────────────────────────────────────

@router.get("/health")
async def ai_health():
    """Return AI provider status including local vision availability."""
    from app.config import settings
    from app.ai.vision_service import _find_ollama_vision_model
    key = (settings.OPENAI_API_KEY or "").strip()
    has_openai = key.startswith("sk-") and key not in PLACEHOLDER_KEYS
    vision_model = await _find_ollama_vision_model()
    return {
        "openai": has_openai,
        "provider": "openai" if has_openai else "keyword_fallback",
        "vision": "openai" if has_openai else (vision_model or "unavailable"),
    }


# ── POST /ai/chat ─────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Main chat endpoint — full intent detection → routing → response pipeline."""

    # Get or create conversation
    conv_id = payload.conversation_id
    if not conv_id:
        conv = AIConversation(
            title=payload.message[:80],
            user_id=current_user.id,
            org_id=current_user.org_id,
        )
        db.add(conv)
        await db.flush()
        conv_id = conv.id

    # Save user message
    user_msg = AIMessage(
        conversation_id=conv_id,
        role="user",
        message=payload.message,
        org_id=current_user.org_id,
        user_id=current_user.id,
    )
    db.add(user_msg)

    # Detect intent
    intent_result = await detect_intent(payload.message)

    # Route to correct pipeline
    route_result = await route_intent(
        intent_result=intent_result,
        message=payload.message,
        user_id=current_user.id,
        org_id=current_user.org_id or 0,
        db=db,
    )

    # Save assistant message with metadata
    ai_msg = AIMessage(
        conversation_id=conv_id,
        role="assistant",
        message=route_result.response,
        intent=route_result.intent,
        confidence=route_result.confidence,
        action_type=route_result.action_type,
        sql_used=route_result.sql_used,
        sources=route_result.sources,
        org_id=current_user.org_id,
        user_id=current_user.id,
    )
    db.add(ai_msg)
    await db.commit()

    return ChatResponse(
        message=route_result.response,
        intent=route_result.intent,
        confidence=route_result.confidence,
        action_type=route_result.action_type,
        sql_used=route_result.sql_used,
        sources=route_result.sources,
        conversation_id=conv_id,
        requires_confirmation=route_result.requires_confirmation,
        pending_action=route_result.pending_action,
    )


# ── POST /ai/confirm ─────────────────────────────────────────────────────
@router.post("/confirm")
async def confirm_action(
    payload: dict,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a previously-confirmed destructive action.
    Payload: {"action_type": "cancel_order", "ref": "PO-002"}
    """
    action_type = payload.get("action_type")
    ref = payload.get("ref")

    if not action_type or not ref:
        raise HTTPException(status_code=400, detail="action_type and ref are required")

    org_id = current_user.org_id or 0
    user_id = current_user.id

    if action_type == "cancel_order":
        from app.services.production_service import cancel_order
        result = await cancel_order(db, ref, org_id, user_id)
        return {"success": result.get("success", False), "message": result.get("message")}

    elif action_type == "cancel_shipment":
        from app.services.shipment_service import cancel_shipment
        result = await cancel_shipment(db, ref, org_id)
        return {"success": result.get("success", False), "message": result.get("message")}

    raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")


# ── GET /ai/conversations ─────────────────────────────────────────────────

@router.get("/conversations")
async def get_conversations(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.user_id == current_user.id)
        .order_by(AIConversation.updated_at.desc())
        .limit(50)
    )
    convs = result.scalars().all()
    return [{"id": c.id, "title": c.title, "created_at": str(c.created_at)} for c in convs]


# ── GET /ai/conversations/{id}/messages ───────────────────────────────────

@router.get("/conversations/{conv_id}/messages")
async def get_messages(
    conv_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIMessage)
        .where(AIMessage.conversation_id == conv_id)
        .where(AIMessage.org_id == current_user.org_id)
        .order_by(AIMessage.created_at.asc())
    )
    msgs = result.scalars().all()
    return [{"id": m.id, "role": m.role, "message": m.message,
             "intent": m.intent, "confidence": m.confidence,
             "action_type": m.action_type, "sql_used": m.sql_used,
             "sources": m.sources, "created_at": str(m.created_at)} for m in msgs]


# ── POST /ai/voice/chat ───────────────────────────────────────────────────

@router.post("/voice/chat")
async def voice_chat(
    audio: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Voice input → full AI pipeline → voice output."""
    from app.ai.voice_service import voice_chat as vc
    audio_bytes = await audio.read()
    result = await vc(audio_bytes, current_user.id, current_user.org_id or 0, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Return audio if available
    if result.get("audio_bytes"):
        return Response(
            content=result["audio_bytes"],
            media_type="audio/mpeg",
            headers={
                "X-Transcript": result.get("transcript", ""),
                "X-AI-Response": result.get("ai_response", ""),
                "X-Intent": result.get("intent", ""),
                "X-Confidence": str(result.get("confidence", 0)),
            }
        )
    return result


# ── POST /ai/voice/transcribe ─────────────────────────────────────────────

@router.post("/voice/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user),
):
    from app.ai.voice_service import transcribe_audio
    audio_bytes = await audio.read()
    return await transcribe_audio(audio_bytes, audio.filename or "audio.webm")


# ── POST /ai/voice/speak ──────────────────────────────────────────────────

@router.post("/voice/speak")
async def speak(
    payload: dict,
    current_user: UserRead = Depends(get_current_user),
):
    from app.ai.voice_service import text_to_speech
    text = payload.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    audio = await text_to_speech(text, payload.get("voice"))
    return Response(content=audio, media_type="audio/mpeg")


# ── POST /ai/vision/analyze ───────────────────────────────────────────────

@router.post("/vision/analyze")
async def vision_analyze(
    image: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user),
):
    """Upload image → GPT-4o Vision (or Ollama llava fallback) → defect/label analysis."""
    import base64
    from app.ai.vision_service import analyze_image

    image_bytes = await image.read()
    media_type  = image.content_type or "image/jpeg"
    b64         = base64.b64encode(image_bytes).decode()
    data_url    = f"data:{media_type};base64,{b64}"

    result = await analyze_image(data_url, image_bytes=image_bytes)
    return result


# ── WebSocket /ai/ws/{conv_id} ────────────────────────────────────────────

@router.websocket("/ws/{conv_id}")
async def websocket_chat(websocket: WebSocket, conv_id: int):
    """
    WebSocket streaming chat.
    Receives: {"message": "...", "token": "..."}
    Sends:    {"type": "intent", "intent": "...", "confidence": 0.9}
              {"type": "token", "content": "..."}  (word by word)
              {"type": "done", "sql_used": "...", "sources": [...]}
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            access_token = data.get("token", "")

            if not message:
                continue

            # Validate token
            try:
                from app.core.security import decode_access_token
                from app.database import AsyncSessionLocal
                payload = decode_access_token(access_token)
                user_id = int(payload.get("sub", 0))
                org_id  = int(payload.get("org_id") or 0)
                role    = payload.get("role", "viewer")
            except Exception:
                await websocket.send_json({"type": "error", "content": "Invalid token"})
                continue

            async with AsyncSessionLocal() as db:
                # Detect intent and send immediately
                intent_result = await detect_intent(message)
                await websocket.send_json({
                    "type": "intent",
                    "intent": intent_result.intent,
                    "confidence": intent_result.confidence,
                    "action_type": intent_result.action_type,
                })

                # Route and get response
                route_result = await route_intent(
                    intent_result, message, user_id, org_id, db
                )

                # Stream tokens while preserving whitespace (including \n) for markdown
                import re as _re
                tokens = _re.findall(r'\S+|\s+', route_result.response)
                for token in tokens:
                    await websocket.send_json({"type": "token", "content": token})
                    if token.strip():
                        await asyncio.sleep(0.018)

                # Send completion signal
                await websocket.send_json({
                    "type": "done",
                    "sql_used": route_result.sql_used,
                    "sources": route_result.sources,
                    "requires_confirmation": route_result.requires_confirmation,
                    "pending_action": route_result.pending_action,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass
