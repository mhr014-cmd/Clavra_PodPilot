from pydantic import BaseModel
from typing import Optional, Any
import datetime


class IntentResult(BaseModel):
    intent: str
    confidence: float
    entities: dict = {}
    action_type: str
    reasoning: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class RouteResult(BaseModel):
    intent: str
    confidence: float
    action_type: str
    response: str
    data: Optional[Any] = None
    sql_used: Optional[str] = None
    sources: Optional[list] = None
    error: Optional[str] = None
    # Confirmation flow
    requires_confirmation: bool = False
    pending_action: Optional[dict] = None   # {"type": "cancel_order", "ref": "PO-002", ...}


class ChatResponse(BaseModel):
    message: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    action_type: Optional[str] = None
    sql_used: Optional[str] = None
    sources: Optional[list] = None
    conversation_id: Optional[int] = None
    timestamp: str = ""
    # Confirmation flow
    requires_confirmation: bool = False
    pending_action: Optional[dict] = None

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        super().__init__(**data)
