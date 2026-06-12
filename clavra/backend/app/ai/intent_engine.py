"""
Intent Detection Engine — Clavra ProdPilot™
Classifies user messages into one of 14 manufacturing intents.
Uses GPT-4o with json_object mode. Falls back to Ollama for local dev.
"""
import json
import re
from app.config import settings
from app.schemas.ai_schema import IntentResult

INTENT_SYSTEM_PROMPT = """You are an intent classifier for Clavra ProdPilot™ — a manufacturing ERP AI system.

Classify the user query into EXACTLY ONE of these intents:
- greeting
- general_status
- help
- cancel_order
- get_order_status
- get_last_orders
- get_active_orders
- production_line_status
- count_orders
- production_efficiency
- shipment_status
- cancel_shipment
- delay_prediction
- inventory_check
- defect_analysis
- ask_policy
- ask_manual
- create_invoice
- quality_report
- create_order
- book_shipment
- update_order_status
- log_quality
- link_order_to_shipment
- unknown

Use "greeting" for: hello, hi, hey, good morning, how are you, etc. — ONLY when the message is purely a social greeting with NO operational reference.
Use "general_status" for: summary, overview, what's happening, how's everything, any issues, status report, factory status — ONLY when NO specific order/shipment reference is present.
Use "get_order_status" for: any message that contains an order reference (PO-001, ORD-002, P004, PO004, etc.) combined with words like status, check, where is, what is, how is, update, packing, sewing. Examples: "P004 what is the status", "PO-001 status", "how is order P003", "what stage is PO005".
Use "get_last_orders" for: ANY request to SEE, LIST, or SHOW all production orders/order numbers. Examples: "Show me the order numbers", "Show all orders", "List my orders", "What orders do I have?", "Give me the order list", "What are my PO numbers?", "Display all production orders".
Use "get_active_orders" for: requests specifically about what is CURRENTLY RUNNING or IN PROGRESS in production. Examples: "What are running in production?", "What's in production right now?", "What orders are active?", "What's being sewn?", "What's being cut?", "What's currently in production?", "Which orders are on the floor?", "Show me orders in progress".
Use "production_line_status" for: requests about specific production LINES (Line A, Line B, etc.) or which line is running what. Examples: "Show me production line status", "What is Line A running?", "Which orders are on Line B?", "Line status report", "Show me the lines", "What's running on each line?", "Production floor status".
Use "inventory_check" for: requests about stock levels, quantities, materials on hand — e.g. "How much cotton do I have?", "Is fabric low?", "Check my stock". NEVER use this for SOP, procedure, or document queries.
Use "ask_policy" for: requests about compliance rules, regulations, audit requirements, quality standards — e.g. "What is the quality policy?", "Show me the compliance checklist".
Use "ask_manual" for: requests about SOPs, work instructions, procedures, manuals, how-to guides — e.g. "Fabric Inspection SOP", "Cutting procedure", "Sewing manual", "What is the SOP for packing?", "Show me the inspection procedure". ALWAYS use "ask_manual" when the message contains the word "SOP", "procedure", "manual", "work instruction", or "how to" — even if other material words like "fabric" are present.
Use "help" ONLY for meta-questions about what the AI can do — NOT for data retrieval. Examples of CORRECT help: "what can you do", "help me", "show me what commands you have", "what are your features", "what are your capabilities". Examples of WRONG help (these should be get_last_orders/shipment_status/etc): "Show me the order numbers" (get_last_orders), "Show all shipments" (shipment_status), "List my inventory" (inventory_check).

Use "create_order" for: requests to create/place/add a NEW production order. Examples: "Create order for H&M 5000 pieces", "New production order for Zara Summer Dress", "Place order 3000 units for Next". ONLY when user wants to CREATE something new.
Use "book_shipment" for: requests to book/create/add a new shipment. Examples: "Book shipment to Hamburg", "New shipment via Maersk for PO-001", "Create shipment to London". ONLY when user wants to CREATE a new shipment.
Use "update_order_status" for: requests to change/move/update/set the STATUS or STAGE of an existing order. Examples: "Move PO-001 to Cutting", "Mark PO-002 as Sewing", "Update PO-003 to Packing", "Set order to Completed".
Use "log_quality" for: requests to LOG/RECORD/ADD defects, rejects, or quality issues to an order. Examples: "Log 30 defects for PO-001", "Record 50 rejects type stain", "Mark 20 pieces defective for PO-002".
Use "link_order_to_shipment" for: requests to LINK/CONNECT/ATTACH/ASSIGN a production order to a shipment. Examples: "Link PO-001 to SHP-002", "Link order PO 006 in shipment SHP-001", "Attach order to shipment", "Connect PO-003 with SHP-004", "Link another orders in shipment". Extract order_no and shipment_no when present.

CRITICAL RULE: The word "SOP" always means "ask_manual". "Fabric Inspection SOP" → ask_manual (NOT inventory_check). "Cutting SOP" → ask_manual. Any query containing "SOP", "procedure", "manual", or "work instruction" is ALWAYS ask_manual or ask_policy, never inventory_check.

IMPORTANT: If a message contains an order number (even without a dash, like P004 or PO004) AND asks about status, ALWAYS use "get_order_status", never "general_status". Extract the order number into entities.order_no, normalising P004 → PO-004 and PO004 → PO-004.

ENTITY KEY NAMES — always use these exact keys:
- create_order: {"buyer": "H&M", "quantity": 5000, "style": "Summer Dress"}
- book_shipment: {"destination": "Hamburg", "carrier": "Maersk", "order_no": "PO-001"}
- update_order_status: {"order_no": "PO-001", "new_status": "Cutting"}
- log_quality: {"order_no": "PO-001", "defect_qty": 30, "defect_type": "stain"}
- link_order_to_shipment: {"order_no": "PO-006", "shipment_no": "SHP-002"}
- get_order_status / cancel_order: {"order_no": "PO-001"}
- cancel_shipment: {"shipment_no": "SHP-001"}

Determine the action_type:
- business_action     → requires calling a specific backend method (cancel, create, update)
- analytics_question  → requires generating and running a SQL query (count, sum, trend)
- knowledge_question  → requires searching uploaded documents (policy, manual, SOP)
- vision_request      → requires analyzing an image (defect, label, photo)
- unknown             → unclear, needs clarification

Extract all entities: order IDs, buyer names, dates, quantities, line numbers, etc.

Respond ONLY in this exact JSON format — no other text:
{
  "intent": "intent_name",
  "confidence": 0.95,
  "entities": {"key": "value"},
  "action_type": "business_action",
  "reasoning": "one sentence explaining the classification"
}"""

INTENT_ACTION_MAP = {
    "greeting":              "business_action",
    "general_status":        "business_action",
    "help":                  "business_action",
    "cancel_order":          "business_action",
    "get_order_status":      "business_action",
    "get_last_orders":       "business_action",
    "get_active_orders":     "business_action",
    "production_line_status":"business_action",
    "count_orders":          "analytics_question",
    "production_efficiency": "business_action",
    "shipment_status":       "business_action",
    "cancel_shipment":       "business_action",
    "delay_prediction":      "business_action",
    "inventory_check":       "business_action",
    "defect_analysis":       "vision_request",
    "ask_policy":            "knowledge_question",
    "ask_manual":            "knowledge_question",
    "create_invoice":        "business_action",
    "quality_report":        "analytics_question",
    "create_order":          "business_action",
    "book_shipment":         "business_action",
    "update_order_status":   "business_action",
    "log_quality":           "business_action",
    "link_order_to_shipment":"business_action",
    "unknown":               "unknown",
}


PLACEHOLDER_KEYS = {"sk-your-openai-key-here", "sk-xxxx", "sk-placeholder", ""}

async def detect_intent(message: str) -> IntentResult:
    """
    Detect intent from a user message.
    Priority: OpenAI (8s timeout) → keyword rules → Ollama (for ambiguous only).
    Keyword rules cover all 14 intents and return instantly — Ollama is only
    used when keywords return 'unknown' to avoid blocking the event loop.
    """
    key = (settings.OPENAI_API_KEY or "").strip()
    if key.startswith("sk-") and key not in PLACEHOLDER_KEYS:
        try:
            return await _detect_with_openai(message)
        except Exception:
            pass

    # Fast keyword match — covers the vast majority of queries instantly
    kw_result = _detect_with_keywords(message)
    if kw_result.intent != "unknown":
        return kw_result

    # Only call Ollama when keywords can't classify (rare edge cases)
    try:
        return await _detect_with_ollama(message)
    except Exception:
        pass

    return kw_result  # return the "unknown" result


async def _detect_with_openai(message: str) -> IntentResult:
    """Use GPT-4o with json_object response format."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user",   "content": message}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=300,
        timeout=8.0,
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)
    return _build_result(data)


async def _detect_with_ollama(message: str) -> IntentResult:
    """Fallback — Ollama for local development."""
    from app.ai.ollama_service import ask_ollama

    prompt = f"{INTENT_SYSTEM_PROMPT}\n\nUser message: {message}\n\nRespond with JSON only."
    raw = await ask_ollama(prompt)

    # Extract JSON from response
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return _build_result(data)
        except json.JSONDecodeError:
            pass

    # Ultimate fallback
    return IntentResult(
        intent="unknown",
        confidence=0.0,
        entities={},
        action_type="unknown",
        reasoning="Could not parse AI response"
    )


def _build_result(data: dict) -> IntentResult:
    """Validate and build IntentResult from parsed JSON."""
    intent = data.get("intent", "unknown")
    confidence = float(data.get("confidence", 0.0))

    # Override action_type from our canonical map if available
    action_type = INTENT_ACTION_MAP.get(intent, data.get("action_type", "unknown"))

    return IntentResult(
        intent=intent,
        confidence=min(max(confidence, 0.0), 1.0),
        entities=data.get("entities", {}),
        action_type=action_type,
        reasoning=data.get("reasoning", "")
    )


KEYWORD_RULES: list[tuple[list[str], str]] = [
    # Meta intents — must come first (most specific)
    (["hello", "hi ", "hey", "good morning", "good afternoon", "greetings", "howdy"],
                                                                                       "greeting"),
    (["summary", "overview", "what's happening", "how is everything", "any issue",
      "status report", "factory status", "dashboard", "give me a summary",
      "factory summary", "give me a factory", "full summary", "everything at once",
      "how's everything", "how are things", "what's going on"],                        "general_status"),
    # "help" only for capability/meta questions — NOT for data retrieval
    (["what can you do", "show command", "list feature", "list command",
      "your capabilities", "what commands", "what features"],                          "help"),
    # CRUD create/update operations — must come BEFORE cancel/get rules
    (["create order", "new order", "add order", "place order", "make order",
      "create production order", "new production order",
      "add production order"],                                                          "create_order"),
    (["book shipment", "new shipment", "create shipment", "add shipment",
      "schedule shipment", "book new shipment"],                                       "book_shipment"),
    (["link order", "link another order", "link orders in shipment",
      "attach order", "connect order", "assign order to shipment",
      "link po", "link p0", "link production order",
      "link in shipment", "link to shipment", "add order to shipment"],               "link_order_to_shipment"),
    (["move order", "move po-", "update order status", "change order status",
      "set order status", "mark order as", "set po-", "update po-",
      "change status to", "update status to",
      "move to cutting", "move to sewing", "move to finishing",
      "move to packing", "move to completed",
      "set to cutting", "set to sewing", "set to packing"],                           "update_order_status"),
    (["log defect", "log defects", "record defect", "add defect",
      "log reject", "record reject", "defects for", "rejects for",
      "defects found", "pieces defective", "units defective",
      "mark defective", "log quality issue"],                                         "log_quality"),
    # Business actions — order operations
    (["cancel shipment", "cancel ship"],                                               "cancel_shipment"),
    (["cancel", "cancell"],                                                            "cancel_order"),
    # Active / in-progress orders — "what's running in production"
    (["running in production", "what is in production", "what's in production",
      "currently in production", "in progress", "orders in progress",
      "active orders", "on the floor", "being cut", "being sewn",
      "currently running", "what are running", "what is running",
      "in production now", "production floor"],                                        "get_active_orders"),
    # Production line status — specific to lines
    (["production line status", "line status", "line a", "line b", "line c",
      "which line", "what line", "show me lines", "show lines",
      "line report", "floor status", "running on each", "which order on",
      "order on line", "line assignment", "production lines", "how many lines",
      "lines running", "lines are running", "how many production line",
      "production floor"],                                                              "production_line_status"),
    # Data retrieval — show/list/give me orders
    (["show me the order", "show me my order", "show me all order",
      "give me the order", "give me my order", "list the order",
      "what are my order", "what orders do i", "view my order",
      "see my order", "display order", "order number", "order list",
      "show order", "list order", "my order", "all order",
      "last order", "recent order", "show production",
      "production status", "get my order"],                                            "get_last_orders"),
    (["order status", "where is order", "track order",
      "order no", "ord-", "po-", " po0", " p00", " p0"],                              "get_order_status"),
    (["status", "where is"],                                                           "get_order_status"),
    (["how many order", "count order", "total order"],                                 "count_orders"),
    (["efficiency", "production rate", "output rate", "line efficiency"],              "production_efficiency"),
    # Shipments
    (["show me the shipment", "show me my shipment", "list shipment",
      "what shipments", "view shipment", "my shipments", "all shipment"],              "shipment_status"),
    (["shipment", "ship", "delivery", "consignment"],                                  "shipment_status"),
    (["delay", "late", "overdue", "at risk"],                                          "delay_prediction"),
    # ── Knowledge / Documents — MUST come before broad inventory terms ──────
    # (queries like "Fabric Inspection SOP" contain "fabric" which also matches
    #  inventory_check; by putting these rules first they capture document queries)
    (["policy", "rule", "compliance", "regulation", "standard",
      "audit", "checklist", "requirement"],                                            "ask_policy"),
    (["sop", "manual", "guide", "procedure", "instruction",
      "fabric inspection", "inspection sop", "cutting sop", "sewing sop",
      "packing sop", "qc sop", "quality sop", "finishing sop",
      "fabric sop", "how to", "work instruction", "standard operating"],              "ask_manual"),
    # ── Inventory ─────────────────────────────────────────────────────────
    (["show me the inventory", "show my inventory", "show stock",
      "list stock", "what stock", "my materials", "view inventory"],                   "inventory_check"),
    (["inventory", "stock", "material", "fabric", "quantity",
      "running low", "low on", "out of stock", "shortage"],                           "inventory_check"),
    # Other
    (["defect", "fault", "image", "photo", "scan"],                                    "defect_analysis"),
    (["invoice", "bill", "receipt"],                                                    "create_invoice"),
    (["quality", "qc", "inspection", "reject"],                                         "quality_report"),
    # help as final catch-all for "help" keyword alone
    (["help"],                                                                          "help"),
]


def _detect_with_keywords(message: str) -> IntentResult:
    """Rule-based fallback when no AI provider is available."""
    msg = message.lower()
    for keywords, intent in KEYWORD_RULES:
        if any(kw in msg for kw in keywords):
            action_type = INTENT_ACTION_MAP.get(intent, "unknown")
            return IntentResult(
                intent=intent,
                confidence=0.80,
                entities={},
                action_type=action_type,
                reasoning=f"Keyword match for '{intent}' (no AI provider configured)",
            )
    return IntentResult(
        intent="unknown",
        confidence=0.0,
        entities={},
        action_type="unknown",
        reasoning="No AI provider configured. Add OPENAI_API_KEY to backend/.env to enable full AI.",
    )
