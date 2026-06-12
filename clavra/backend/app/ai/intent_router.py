"""
Intent Router — Clavra ProdPilot™
Routes detected intent to the correct execution pipeline.
Branches: A (backend), B (SQL), C (RAG), V (Vision), D (Clarify)
"""
import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.ai_schema import IntentResult, RouteResult
from app.config import settings


def _normalise_order_ref(raw: str) -> str:
    """
    Normalise any order-ref variant to canonical PO-NNN / ORD-NNN form.
    Handles: PO-004, PO004, P004, P0-004, ORD001, ORD-001
    """
    r = raw.strip().upper().replace(" ", "")
    # ORD variants
    r = re.sub(r'^ORD-?(\d+)$', r'ORD-\1', r)
    # PO variants: PO-004 stays, PO004 → PO-004
    r = re.sub(r'^PO-?(\d+)$', r'PO-\1', r)
    # P variants: P004, P0004 → PO-4 or PO-04 — keep leading zeros
    r = re.sub(r'^P(\d+)$', r'PO-\1', r)
    return r


def _extract_order_ref(message: str, entities: dict) -> str | None:
    """Extract order reference — PO-/ORD- and shorthand P004 patterns, never SHP-."""
    ref = entities.get("order_id") or entities.get("order_no") or entities.get("order")
    if ref:
        s = str(ref).strip()
        if not re.match(r'^SH', s, re.IGNORECASE):
            return _normalise_order_ref(s)
    # Pre-normalise voice-transcribed forms: "PO 001" / "P O 001" → "PO001"
    scan = re.sub(r'\bP\s*O\s+(\d+)\b', r'PO\1', message, flags=re.IGNORECASE)
    scan = re.sub(r'\bORD\s+(\d+)\b', r'ORD\1', scan, flags=re.IGNORECASE)
    # Regex: PO-003, PO003, P004, ORD-001 — explicitly exclude SHP-/SH-
    m = re.search(r'\b(PO-?\d+|ORD-?\d+|P\d{2,})\b', scan, re.IGNORECASE)
    if m:
        candidate = m.group()
        # exclude SHP/SH prefix (redundant safety check)
        if not re.match(r'^SH', candidate, re.IGNORECASE):
            return _normalise_order_ref(candidate)
    return None


def _extract_shipment_ref(message: str, entities: dict) -> str | None:
    """Extract shipment reference — SHP-/SH- patterns."""
    ref = entities.get("shipment_no") or entities.get("shipment_id") or entities.get("shipment")
    if ref:
        return str(ref).strip().upper()
    m = re.search(r'\b(SHP|SH|SHIP)-?\s*\d+\b', message, re.IGNORECASE)
    if m:
        return m.group().replace(' ', '').upper()
    return None


def _smart_detect_ref(message: str, entities: dict) -> tuple[str | None, str]:
    """
    Auto-detect whether a reference is an order or shipment.
    Returns (ref, "order"|"shipment"|"unknown").
    """
    ship_ref = _extract_shipment_ref(message, entities)
    if ship_ref:
        return ship_ref, "shipment"
    order_ref = _extract_order_ref(message, entities)
    if order_ref:
        return order_ref, "order"
    return None, "unknown"


def _extract_item_ref(message: str, entities: dict) -> str | None:
    """Extract inventory item reference from GPT entities or message."""
    return (
        entities.get("item_code") or entities.get("material")
        or entities.get("item") or entities.get("product")
    )


_VALID_STATUSES = ["Pending", "Cutting", "Sewing", "Finishing", "Packing", "Completed"]
_STATUS_ALIASES = {
    "complete": "Completed", "finish": "Completed", "finished": "Completed",
    "done": "Completed", "cut": "Cutting", "sew": "Sewing",
    "pack": "Packing", "packing": "Packing",
}


_BUYER_STOP = {"me", "us", "the", "my", "a", "an", "new", "order", "shipment",
               "create", "add", "place", "make", "production"}


def _extract_create_order_entities(message: str, entities: dict) -> dict:
    """Extract buyer, quantity, style from a create-order message (keyword-mode fallback).
    Handles both typed text and voice-transcribed input (lowercase, missing keywords).
    """
    result = dict(entities)

    # ── Quantity: "5000 pieces / pcs / units" ─────────────────────────────
    m = re.search(r'(\d[\d,]*)\s*(pieces?|pcs?|units?|qty)', message, re.IGNORECASE)
    if m and "quantity" not in result:
        result["quantity"] = int(m.group(1).replace(",", ""))

    # ── Buyer option 1: "for [Buyer]" before quantity or end ──────────────
    if "buyer" not in result:
        m = re.search(
            r'\bfor\s+([A-Za-z][A-Za-z0-9&\s\-\.]+?)(?:\s*,|\s+\d|\s+with\b|\s+of\b'
            r'|\s+style\b|\s+deliver\b|\s+due\b|\s*$)', message, re.IGNORECASE
        )
        if m:
            b = m.group(1).strip().rstrip(",")
            if b.lower() not in _BUYER_STOP and not re.match(
                r'^(?:create|new|add|place|make)\b', b, re.IGNORECASE
            ):
                result["buyer"] = b

    # ── Buyer option 2: word(s) BEFORE the quantity (voice: "h&m 5000 pcs") ──
    if "buyer" not in result and "quantity" in result:
        qty_pos = re.search(rf'\b{re.escape(str(result["quantity"]))}\b', message)
        if qty_pos:
            before = message[:qty_pos.start()].strip()
            # Strip "create/new/add order" prefix
            before = re.sub(
                r'^(?:create|new|add|place|make)\s+(?:production\s+)?order\s*(?:for\s*)?',
                '', before, flags=re.IGNORECASE
            ).strip().rstrip(",").strip()
            if before and len(before) > 1 and before.lower() not in _BUYER_STOP:
                result["buyer"] = before

    # ── Style option 1: "style [Style]" ───────────────────────────────────
    if "style" not in result:
        m = re.search(
            r'\bstyle\s+([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s*,|\s+\d|\s+deliver\b|\s+due\b|\s*$)',
            message, re.IGNORECASE
        )
        if m:
            result["style"] = m.group(1).strip()

    # ── Style option 2: "of [Style]" ─────────────────────────────────────
    if "style" not in result:
        m = re.search(
            r'\bof\s+([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s*,|\s+\d|\s+deliver\b|\s+due\b|\s*$)',
            message, re.IGNORECASE
        )
        if m:
            result["style"] = m.group(1).strip()

    # ── Style option 3: "[qty] pieces for [Style]" (voice) ───────────────
    if "style" not in result:
        m = re.search(
            r'\d+\s*(?:pieces?|pcs?|units?)\s+for\s+([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s*,|\s*$)',
            message, re.IGNORECASE
        )
        if m:
            result["style"] = m.group(1).strip()

    # ── Style option 4: "[qty] units [Style]" — style directly after units ──
    if "style" not in result and "quantity" in result:
        m = re.search(
            rf'\b{re.escape(str(result["quantity"]))}\b\s*(?:pieces?|pcs?|units?)\s+'
            r'([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s*,|\s*$)',
            message, re.IGNORECASE
        )
        if m:
            s = m.group(1).strip()
            # Don't capture connector words as style
            if s.lower() not in ("for", "of", "the", "a", "an"):
                result["style"] = s

    return result


def _extract_book_shipment_entities(message: str, entities: dict) -> dict:
    """Extract destination, carrier, linked order from a book-shipment message."""
    result = dict(entities)
    # Destination: "to Hamburg" / "to london" (voice: lowercase)
    m = re.search(
        r'\bto\s+([A-Za-z][A-Za-z\s,]+?)(?:\s+via\b|\s+by\b|\s+through\b|\s+for\b'
        r'|\s+carrier\b|\s+link\b|\s*,|\s*$)', message, re.IGNORECASE
    )
    if m and "destination" not in result:
        result["destination"] = m.group(1).strip().rstrip(",")
    # Carrier: "via Maersk" / "carrier DHL"
    m = re.search(
        r'\b(?:via|by|carrier|through)\s+([A-Za-z][A-Za-z0-9\s]+?)(?:\s*,|\s+for\b'
        r'|\s+link\b|\s+to\b|\s*$)', message, re.IGNORECASE
    )
    if m and "carrier" not in result:
        result["carrier"] = m.group(1).strip()
    # Linked order ref
    if "order_no" not in result:
        ref = _extract_order_ref(message, {})
        if ref:
            result["order_no"] = ref
    return result


def _extract_update_status_entities(message: str, entities: dict) -> dict:
    """Extract order ref and new status from an update-status message."""
    result = dict(entities)
    # Status from known list
    msg_l = message.lower()
    for s in _VALID_STATUSES:
        if s.lower() in msg_l and "new_status" not in result:
            result["new_status"] = s
    # Alias normalisation
    if "new_status" not in result:
        for alias, canonical in _STATUS_ALIASES.items():
            if alias in msg_l:
                result["new_status"] = canonical
                break
    # Order ref
    if "order_no" not in result:
        ref = _extract_order_ref(message, entities)
        if ref:
            result["order_no"] = ref
    return result


def _extract_log_quality_entities(message: str, entities: dict) -> dict:
    """Extract defect count, type, and order ref from a log-quality message."""
    result = dict(entities)
    # Defect quantity: "30 defects / rejects / pieces defective"
    m = re.search(
        r'(\d+)\s*(defects?|rejects?|pieces?\s+defective|units?\s+defective)',
        message, re.IGNORECASE
    )
    if m and "defect_qty" not in result:
        result["defect_qty"] = int(m.group(1))
    # Defect type: "type: stain" / "issue: tear"
    m = re.search(
        r'(?:type[:\s]+|issue[:\s]+|problem[:\s]+)([A-Za-z][A-Za-z\s]+?)(?:\s*,|\s*$)',
        message, re.IGNORECASE
    )
    if m and "defect_type" not in result:
        result["defect_type"] = m.group(1).strip()
    # Order ref
    if "order_no" not in result:
        ref = _extract_order_ref(message, entities)
        if ref:
            result["order_no"] = ref
    return result


async def route_intent(
    intent_result: IntentResult,
    message: str,
    user_id: int,
    org_id: int,
    db: AsyncSession,
    image_url: str | None = None,
) -> RouteResult:
    """
    Main routing function. Dispatches to correct branch based on action_type.
    """
    # ── Pre-routing overrides ────────────────────────────────────────────────
    import copy as _copy
    _msg_lower = message.lower()
    _status_words = ("status", "stage", "where is", "how is", "what is",
                     "update", "check", "track", "progress")
    # Words that indicate "show me data" (not meta-help)
    _data_show_words = ("show", "list", "give me", "tell me", "what are",
                        "display", "see my", "view", "get me", "fetch",
                        "what's my", "whats my", "what do i have")

    # ── Override 1: general_status/greeting + order ref → get_order_status ──
    if intent_result.intent in ("general_status", "greeting"):
        _ship_probe = _extract_shipment_ref(message, intent_result.entities or {})
        if not _ship_probe:
            _order_probe = _extract_order_ref(message, intent_result.entities or {})
            if _order_probe and any(w in _msg_lower for w in _status_words):
                intent_result = _copy.copy(intent_result)
                intent_result.intent = "get_order_status"
                intent_result.action_type = "business_action"
                intent_result.entities = {**(intent_result.entities or {}),
                                           "order_no": _order_probe}

    # ── Override 2: get_order_status + SHP ref (no order ref) → shipment_status ──
    # Exception: if user explicitly asks about the ORDER linked to a shipment ("order no", "which order"),
    # keep it as get_order_status so the cross-reference logic in _branch_backend can run.
    if intent_result.intent == "get_order_status":
        _ship_probe2 = _extract_shipment_ref(message, intent_result.entities or {})
        _order_probe2 = _extract_order_ref(message, intent_result.entities or {})
        _order_seeking = ("order no", "order number", "which order", "what order",
                          "order linked", "linked order", "order ref", "po number",
                          "production order", "order name")
        _asking_for_order = any(w in _msg_lower for w in _order_seeking)
        if _ship_probe2 and not _order_probe2 and not _asking_for_order:
            intent_result = _copy.copy(intent_result)
            intent_result.intent = "shipment_status"
            intent_result.action_type = "business_action"
            intent_result.entities = {**(intent_result.entities or {}),
                                       "shipment_no": _ship_probe2}
        # Also redirect pure shipment-inquiry messages misclassified as get_order_status
        # e.g. "what about shipment status", "shipment info", "show my shipments"
        elif not _order_probe2 and not _asking_for_order:
            _ship_inquiry = ("shipment status", "about shipment", "my shipment",
                             "all shipment", "recent shipment", "any shipment",
                             "shipment info", "shipment update", "show shipment",
                             "list shipment", "shipping status", "shipment going")
            if any(w in _msg_lower for w in _ship_inquiry):
                intent_result = _copy.copy(intent_result)
                intent_result.intent = "shipment_status"
                intent_result.action_type = "business_action"

    # ── Override 2a: "link order … shipment" → link_order_to_shipment ─────────
    _link_terms = ("link order", "link po", "link another order", "attach order",
                   "connect order", "assign order to", "link in shipment",
                   "link to shipment", "add order to shipment", "link orders in")
    if intent_result.intent not in ("link_order_to_shipment", "book_shipment") and \
            any(w in _msg_lower for w in _link_terms):
        intent_result = _copy.copy(intent_result)
        intent_result.intent = "link_order_to_shipment"
        intent_result.action_type = "business_action"

    # ── Override 2b: any intent + SOP/policy/manual keywords → knowledge route ──
    # Catches "Fabric Inspection SOP" misclassified as inventory_check, general_status, etc.
    _doc_terms = ("sop", "manual", "procedure", "instruction", "policy",
                  "standard operating", "work instruction", "how to",
                  "fabric inspection", "cutting sop", "sewing sop",
                  "packing sop", "qc procedure", "audit", "compliance")
    _non_doc_intents = ("ask_policy", "ask_manual")
    if intent_result.intent not in _non_doc_intents and any(w in _msg_lower for w in _doc_terms):
        _is_policy = any(w in _msg_lower for w in ("policy", "rule", "compliance", "regulation", "audit"))
        intent_result = _copy.copy(intent_result)
        intent_result.intent = "ask_policy" if _is_policy else "ask_manual"
        intent_result.action_type = "knowledge_question"

    # ── Override 3: help misclassification — "show orders/shipments/inventory" ──
    if intent_result.intent == "help":
        _order_terms = ("order", "po-", " po ", "production order", "order no",
                        "order number", "order list", "my orders", "all orders")
        _ship_terms  = ("shipment", "shipping", "shp-", "dispatch", "delivery",
                        "consignment", "my shipments", "all shipments")
        _inv_terms   = ("inventory", "stock", "material", "fabric",
                        "my stock", "materials")
        _line_terms  = ("line", "production line", "floor status", "line a",
                        "line b", "line c", "which line")

        if any(w in _msg_lower for w in _data_show_words):
            if any(w in _msg_lower for w in _line_terms):
                intent_result = _copy.copy(intent_result)
                intent_result.intent = "production_line_status"
                intent_result.action_type = "business_action"
            elif any(w in _msg_lower for w in _order_terms):
                intent_result = _copy.copy(intent_result)
                intent_result.intent = "get_last_orders"
                intent_result.action_type = "business_action"
            elif any(w in _msg_lower for w in _ship_terms):
                intent_result = _copy.copy(intent_result)
                intent_result.intent = "shipment_status"
                intent_result.action_type = "business_action"
            elif any(w in _msg_lower for w in _inv_terms):
                intent_result = _copy.copy(intent_result)
                intent_result.intent = "inventory_check"
                intent_result.action_type = "business_action"

    # ── Override 4: general_status misclassification for production-specific queries ──
    # "What are running in production" / "show me production line status" / "Any shipments going out?"
    if intent_result.intent in ("general_status", "help"):
        _active_terms  = ("running in production", "in production", "in progress",
                          "active order", "currently running", "on the floor",
                          "being cut", "being sewn", "being packed")
        _line_terms2   = ("production line status", "line status", "line a",
                          "line b", "line c", "which line", "what line",
                          "running on each line", "floor status",
                          "production lines", "how many lines", "lines running",
                          "line running", "lines are running", "line are running",
                          "how many production", "production floor",
                          "line efficiency", "line performance")
        # Shipment-related: broad set including "what about shipment", "about shipments"
        _ship_msg_terms = ("any shipment", "shipment going", "going out", "what's going out",
                           "whats going out", "shipping out", "outbound shipment",
                           "shipment today", "shipments today", "about shipment",
                           "what about shipment", "shipment status", "my shipment",
                           "list shipment", "show shipment", "all shipment",
                           "shipment update", "shipment info")
        if any(w in _msg_lower for w in _active_terms):
            intent_result = _copy.copy(intent_result)
            intent_result.intent = "get_active_orders"
            intent_result.action_type = "business_action"
        elif any(w in _msg_lower for w in _line_terms2):
            intent_result = _copy.copy(intent_result)
            intent_result.intent = "production_line_status"
            intent_result.action_type = "business_action"
        elif "ship" in _msg_lower and any(w in _msg_lower for w in _ship_msg_terms):
            intent_result = _copy.copy(intent_result)
            intent_result.intent = "shipment_status"
            intent_result.action_type = "business_action"
        elif any(w in _msg_lower for w in ("efficient", "efficiency", "production rate",
                                            "output rate", "how efficient", "line efficiency",
                                            "how is production", "production performance")):
            intent_result = _copy.copy(intent_result)
            intent_result.intent = "production_efficiency"
            intent_result.action_type = "business_action"

    action = intent_result.action_type
    confidence = intent_result.confidence
    threshold = settings.AI_CONFIDENCE_THRESHOLD

    # Low confidence → ask for clarification (Branch D)
    if confidence < threshold or action == "unknown":
        return await _branch_clarify(intent_result, message)

    # Branch A — Business action (call backend service)
    if action == "business_action":
        return await _branch_backend(intent_result, message, user_id, org_id, db)

    # Branch B — Analytics question (AI SQL generation)
    if action == "analytics_question":
        return await _branch_sql(intent_result, message, user_id, org_id, db)

    # Branch C — Knowledge question (RAG)
    if action == "knowledge_question":
        return await _branch_rag(intent_result, message, org_id, db)

    # Branch V — Vision request
    if action == "vision_request":
        return await _branch_vision(intent_result, message, image_url)

    # Fallback
    return await _branch_clarify(intent_result, message)


# ── Branch A — Backend method call ────────────────────────────────────────

async def _branch_backend(
    intent: IntentResult, message: str,
    user_id: int, org_id: int, db: AsyncSession
) -> RouteResult:
    """Call the appropriate service method based on intent name."""
    from app.services.production_service import (
        cancel_order, get_order_status, get_last_orders, create_invoice
    )
    from app.services.shipment_service import (
        get_shipment_status, get_recent_shipments,
        cancel_shipment, get_shipment_by_order,
    )
    from app.services.inventory_service import check_inventory, get_low_stock_items

    entities = intent.entities
    response_text = ""
    data = None
    requires_confirmation = False
    pending: dict | None = None

    try:
        if intent.intent == "get_active_orders":
            from app.services.production_service import get_active_orders as _get_active
            result = await _get_active(db, org_id)
            data = result
            if not result:
                response_text = (
                    "No orders are currently in active production.\n\n"
                    "*All orders may be Pending, Completed, or Cancelled.*"
                )
            else:
                stage_icon = {"Cutting":"✂️", "Sewing":"🧵", "Finishing":"🪡",
                              "Packing":"📦", "Pending":"🟡"}
                lines = []
                for o in result:
                    icon = stage_icon.get(o["status"], "⚙️")
                    bar  = "█" * (o["progress_pct"] // 10) + "░" * (10 - o["progress_pct"] // 10)
                    lines.append(
                        f"- {icon} **{o['order_no']}** — {o['buyer']} · *{o['style']}*\n"
                        f"  Stage: **{o['status']}** · {o['produced_qty']:,}/{o['quantity']:,} pcs · `{bar}` {o['progress_pct']}%"
                    )
                response_text = (
                    f"**{len(result)} order{'s' if len(result)!=1 else ''} currently in production:**\n\n"
                    + "\n".join(lines)
                )

        elif intent.intent == "production_line_status":
            from app.services.production_service import get_lines_with_orders as _get_lines
            result = await _get_lines(db, org_id)
            data = result
            if not result:
                response_text = "No production lines found. Set up lines in the Production Lines dashboard."
            else:
                status_icon = {"Running":"🟢", "Idle":"🟡", "Maintenance":"🔧", "Stopped":"🔴"}
                blocks = []
                for l in result:
                    icon = status_icon.get(l["status"], "⚪")
                    header = (
                        f"**{icon} {l['line_name']}** — {l['status']} "
                        f"(Eff: {l['efficiency']}% · {l['operators']} operators · "
                        f"Supervisor: {l['supervisor']})"
                    )
                    if l["current_orders"]:
                        order_lines = []
                        for o in l["current_orders"]:
                            stage_icon = {"Cutting":"✂️","Sewing":"🧵","Finishing":"🪡","Packing":"📦","Pending":"🟡"}
                            order_lines.append(
                                f"  → {stage_icon.get(o['status'],'⚙️')} **{o['order_no']}** "
                                f"({o['buyer']} / *{o['style']}*) — {o['status']} · {o['progress_pct']}% done"
                            )
                        blocks.append(header + "\n" + "\n".join(order_lines))
                    else:
                        blocks.append(header + "\n  → *(No active order assigned)*")
                response_text = f"**Production Floor Status — {len(result)} line{'s' if len(result)!=1 else ''}:**\n\n" + "\n\n".join(blocks)

        elif intent.intent == "production_efficiency":
            from app.services.production_service import get_efficiency_summary as _get_eff
            result = await _get_eff(db, org_id)
            data = result
            if not result or not result.get("lines"):
                response_text = (
                    "No production line data found.\n\n"
                    "*Add lines in the Production Lines dashboard to track efficiency.*"
                )
            else:
                lines_data = result["lines"]
                avg_eff = result["avg_efficiency"]
                best = max(lines_data, key=lambda x: x["efficiency"])
                worst = min(lines_data, key=lambda x: x["efficiency"])
                status_icon = {"Running":"🟢","Idle":"🟡","Maintenance":"🔧","Stopped":"🔴"}
                line_rows = []
                for l in sorted(lines_data, key=lambda x: x["efficiency"], reverse=True):
                    eff = l["efficiency"]
                    bar = "█" * (eff // 10) + "░" * (10 - eff // 10)
                    flag = "🟢" if eff >= 90 else "🔵" if eff >= 70 else "🟡" if eff >= 50 else "🔴"
                    out_pct = round(l["actual_output"] / max(l["target_output"], 1) * 100)
                    line_rows.append(
                        f"- {flag} **{l['line_name']}** `{bar}` **{eff}%**"
                        f"  ·  Output: {l['actual_output']:,}/{l['target_output']:,} pcs ({out_pct}%)"
                        f"  ·  {l['operators']} operators  ·  {status_icon.get(l['status'],'⚪')} {l['status']}"
                    )
                response_text = (
                    f"**Production Efficiency — {len(lines_data)} line{'s' if len(lines_data)!=1 else ''}:**\n\n"
                    + "\n".join(line_rows)
                    + f"\n\n**Floor Average: {avg_eff}%**"
                )
                if best["efficiency"] != worst["efficiency"]:
                    response_text += (
                        f"  ·  Top: **{best['line_name']}** ({best['efficiency']}%)"
                        + (f"  ·  ⚠️ Needs attention: **{worst['line_name']}** ({worst['efficiency']}%)" if worst["efficiency"] < 70 else "")
                    )

        elif intent.intent == "greeting":
            import random
            greetings = [
                "Hello! 👋 How can I help you today?",
                "Hi there! 👋 What would you like to check?",
                "Hey! 👋 Ready to help.",
                "Good to see you! 👋 What can I do for you?",
            ]
            response_text = (
                f"{random.choice(greetings)}\n\n"
                "Try asking me:\n"
                "- *'Give me a factory summary'* — full status at a glance\n"
                "- *'How are my orders?'* — production progress\n"
                "- *'Any shipments going out?'* — logistics\n"
                "- *'Am I low on anything?'* — inventory\n"
                "- *'Help'* — see everything I can do"
            )

        elif intent.intent == "general_status":
            from app.services.summary_service import get_factory_snapshot, format_snapshot_message
            snap = await get_factory_snapshot(db, org_id)
            response_text = format_snapshot_message(
                snap,
                greeting="Here's your current factory status:\n"
            )
            data = snap

        elif intent.intent == "help":
            response_text = (
                "Here's what I can do — by **voice or text**:\n\n"
                "**📋 Read orders** — *'Show my orders'*, *'PO-001 status'*, *'Active orders'*\n"
                "**➕ Create order** — *'Create order for H&M, 5000 pcs of Summer Dress'*\n"
                "**🔄 Update stage** — *'Move PO-001 to Cutting'*, *'Mark PO-002 as Packing'*\n"
                "**❌ Cancel** — *'Cancel PO-003'*, *'Cancel shipment SHP-002'*\n"
                "**🚢 Shipments** — *'Book shipment to Hamburg via Maersk'*, *'List shipments'*\n"
                "**📦 Inventory** — *'Check my stock'*, *'Am I low on anything?'*\n"
                "**⚠️ Quality log** — *'Log 30 defects for PO-001, type: stain'*\n"
                "**📊 Analytics** — *'How efficient is production?'*, *'Delay risks'*\n"
                "**📄 Documents** — *'Fabric Inspection SOP'*, *'Quality policy'*\n"
                "**📸 Vision** — Upload an image to detect defects\n\n"
                "Or say **'Give me a summary'** for a full factory overview."
            )

        elif intent.intent == "cancel_order":
            # Smart routing: if user typed SHP-, it's a shipment cancel not order cancel
            ref, ref_type = _smart_detect_ref(message, entities)
            if ref_type == "shipment":
                # Redirect to cancel_shipment confirmation flow
                result = await get_shipment_status(db, ref, org_id)
                if result:
                    response_text = (
                        f"⚠️ **Confirm Shipment Cancellation**\n\n"
                        f"You are about to cancel:\n"
                        f"- **Shipment:** {result.get('shipment_no')}\n"
                        f"- **Destination:** {result.get('destination')}\n"
                        f"- **Status:** {result.get('status')}\n\n"
                        f"This action cannot be undone. Confirm?"
                    )
                    pending = {"type": "cancel_shipment", "ref": ref, "details": result}
                    requires_confirmation = True
                    data = result
                else:
                    response_text = f"Shipment **{ref}** not found."
            elif not ref:
                response_text = (
                    "Which order would you like to cancel? Please include the order number.\n\n"
                    "*Example: 'Cancel PO-003' or 'Cancel order ORD-001'*"
                )
            else:
                # Fetch order details to show in confirmation
                result = await get_order_status(db, ref, org_id)
                if result:
                    response_text = (
                        f"⚠️ **Confirm Order Cancellation**\n\n"
                        f"You are about to cancel:\n"
                        f"- **Order:** {result.get('order_no')}\n"
                        f"- **Buyer:** {result.get('buyer')}\n"
                        f"- **Quantity:** {result.get('quantity'):,} pcs\n"
                        f"- **Current Status:** {result.get('status')}\n\n"
                        f"This action **cannot be undone**. Please confirm."
                    )
                    pending = {"type": "cancel_order", "ref": ref, "details": result}
                    requires_confirmation = True
                    data = result
                else:
                    response_text = (
                        f"Order **{ref}** not found.\n\n"
                        f"*Say 'Show my orders' to see available orders.*"
                    )

        elif intent.intent == "get_order_status":
            order_id = _extract_order_ref(message, entities)
            shipment_hint = _extract_shipment_ref(message, entities)
            if not order_id and shipment_hint:
                # Cross-reference: user asked which order is inside a shipment
                from sqlalchemy import select as _sel
                from app.models.shipment import Shipment as _Ship
                res2 = await db.execute(
                    _sel(_Ship).where(_Ship.shipment_no == shipment_hint,
                                      _Ship.org_id == org_id)
                )
                s_obj = res2.scalar_one_or_none()
                if s_obj and s_obj.order_id:
                    ord_rec = await get_order_status(db, str(s_obj.order_id), org_id)
                    if ord_rec:
                        response_text = (
                            f"Shipment **{shipment_hint}** is linked to:\n\n"
                            f"- **Order:** {ord_rec.get('order_no')}\n"
                            f"- **Buyer:** {ord_rec.get('buyer')}\n"
                            f"- **Status:** {ord_rec.get('status')}\n"
                            f"- **Quantity:** {ord_rec.get('quantity'):,} pcs"
                        )
                        data = ord_rec
                    else:
                        response_text = f"Shipment {shipment_hint} has a linked order but I couldn't retrieve its details."
                else:
                    response_text = f"No production order is linked to shipment **{shipment_hint}**."
            elif not order_id:
                result = await get_last_orders(db, org_id, 50)
                data = result
                if result:
                    status_icon = {"Pending": "🟡", "Cutting": "🔵", "Sewing": "🟢",
                                   "Finishing": "🟣", "Completed": "✅", "Cancelled": "❌"}
                    lines = [
                        f"- {status_icon.get(o['status'], '⚪')} **{o['order_no']}** — {o['buyer']} · *{o['status']}*"
                        for o in result
                    ]
                    response_text = f"Here are your {len(result)} most recent production orders:\n\n" + "\n".join(lines)
                else:
                    response_text = "No production orders found yet."
            else:
                result = await get_order_status(db, order_id, org_id)
                data = result
                if result:
                    pct = round((result.get('produced_qty', 0) / max(result.get('quantity', 1), 1)) * 100)
                    response_text = (
                        f"**Order {result.get('order_no')}** — {result.get('buyer')}\n\n"
                        f"- **Status:** {result.get('status')}\n"
                        f"- **Style:** {result.get('style', 'N/A')}\n"
                        f"- **Quantity:** {result.get('quantity', 0):,} pcs\n"
                        f"- **Produced:** {result.get('produced_qty', 0):,} pcs ({pct}% complete)"
                    )
                else:
                    response_text = (
                        f"I couldn't find order **{order_id}**.\n\n"
                        f"*Tip: Say 'Show all orders' to see a list of available orders.*"
                    )

        elif intent.intent == "get_last_orders":
            limit = int(entities.get("limit") or 50)
            result = await get_last_orders(db, org_id, limit)
            data = result
            if result:
                status_icon = {"Pending": "🟡", "Cutting": "🔵", "Sewing": "🟢",
                               "Finishing": "🟣", "Completed": "✅", "Cancelled": "❌"}
                lines = [
                    f"- {status_icon.get(o['status'], '⚪')} **{o['order_no']}** — {o['buyer']} · *{o['status']}* · {o['quantity']:,} pcs"
                    for o in result
                ]
                response_text = f"Here are your last **{len(result)} orders**:\n\n" + "\n".join(lines)
            else:
                response_text = "No production orders found. Create your first order to get started."

        elif intent.intent == "link_order_to_shipment":
            from app.services.production_service import link_order_to_shipment_ai
            order_ref    = _extract_order_ref(message, entities)
            shipment_ref = _extract_shipment_ref(message, entities)

            if not order_ref and not shipment_ref:
                response_text = (
                    "Please tell me which order to link and to which shipment.\n\n"
                    "*Example: \"Link PO-006 to SHP-002\"*\n"
                    "*Or: \"Create new shipment for PO-006 to Hamburg via Maersk\"*"
                )
            elif not order_ref:
                response_text = (
                    f"Which production order should I link to **{shipment_ref}**?\n\n"
                    f"*Say e.g. \"Link PO-006 to {shipment_ref}\"*"
                )
            elif not shipment_ref:
                # No shipment specified — offer two paths: link to existing OR create new
                available = await get_recent_shipments(db, org_id, 50)
                data = available
                if available:
                    shp_lines = [
                        f"- **{s['shipment_no']}** → {s['destination'] or 'N/A'} · *{s['status']}*"
                        for s in available
                    ]
                    existing_block = "\n".join(shp_lines)
                    response_text = (
                        f"How would you like to proceed for **{order_ref}**?\n\n"
                        f"**Option A — Link to an existing shipment:**\n"
                        f"{existing_block}\n\n"
                        f"**Option B — Create a new shipment:**\n"
                        f"Say the destination and carrier\n\n"
                        f"*Reply e.g. \"Link {order_ref} to SHP-001\"*\n"
                        f"*Or: \"Book new shipment for {order_ref} to Hamburg via Maersk\"*"
                    )
                else:
                    response_text = (
                        f"No existing shipments found for **{order_ref}**.\n\n"
                        f"**Create a new shipment:**\n"
                        f"*Say e.g. \"Book new shipment for {order_ref} to Hamburg via Maersk\"*"
                    )
            else:
                result = await link_order_to_shipment_ai(db, order_ref, shipment_ref, org_id)
                data = result
                response_text = result["message"]

        elif intent.intent == "shipment_status":
            shipment_no = _extract_shipment_ref(message, entities)
            if not shipment_no:
                result = await get_recent_shipments(db, org_id, 50)
                data = result
                if result:
                    status_icon = {"Pending": "🟡", "In Transit": "🚢", "Customs": "🔵",
                                   "Delivered": "✅", "Delayed": "🔴", "Cancelled": "❌"}
                    lines = [
                        f"- {status_icon.get(s['status'], '⚪')} **{s['shipment_no']}** → {s['destination']} · *{s['status']}*"
                        + (f" · ETA {s['eta'][:10]}" if s.get('eta') else "")
                        for s in result
                    ]
                    response_text = f"Here are your **{len(result)} recent shipments**:\n\n" + "\n".join(lines)
                else:
                    response_text = "No shipments found."
            else:
                result = await get_shipment_status(db, shipment_no, org_id)
                data = result
                if result:
                    response_text = (
                        f"**Shipment {result.get('shipment_no')}**\n\n"
                        f"- **Destination:** {result.get('destination')}\n"
                        f"- **Buyer:** {result.get('buyer', 'N/A')}\n"
                        f"- **Status:** {result.get('status')}\n"
                        + (f"- **ETA:** {str(result.get('eta'))[:10]}\n" if result.get('eta') else "")
                    )
                else:
                    response_text = (
                        f"Shipment **{shipment_no}** not found.\n\n"
                        f"*Say 'Show all shipments' to see available shipments.*"
                    )

        elif intent.intent == "inventory_check":
            item = _extract_item_ref(message, entities)
            if not item:
                result = await get_low_stock_items(db, org_id, 10)
                data = result
                if result:
                    status_icon = {"Low Stock": "🟡", "Critical": "🔴", "Out of Stock": "⛔", "OK": "✅"}
                    lines = [
                        f"- {status_icon.get(i['status'], '⚪')} **{i['material_name']}** — "
                        f"{i['available_qty']} {i['unit']} · *{i['status']}*"
                        for i in result
                    ]
                    response_text = f"**Inventory overview** ({len(result)} items):\n\n" + "\n".join(lines)
                else:
                    response_text = "No inventory records found."
            else:
                result = await check_inventory(db, item, org_id)
                data = result
                if result:
                    response_text = (
                        f"**{result.get('material_name')}** ({result.get('material_code')})\n\n"
                        f"- **Available:** {result.get('available_qty')} {result.get('unit')}\n"
                        f"- **Total Stock:** {result.get('stock_qty', 'N/A')} {result.get('unit')}\n"
                        f"- **Category:** {result.get('category', 'N/A')}\n"
                        f"- **Status:** {result.get('status')}"
                    )
                else:
                    response_text = (
                        f"No inventory record found for *'{item}'*.\n\n"
                        f"*Try 'Check my stock' to see all inventory items.*"
                    )

        elif intent.intent == "cancel_shipment":
            shipment_no = _extract_shipment_ref(message, entities)
            if not shipment_no:
                response_text = (
                    "Which shipment would you like to cancel?\n\n"
                    "*Example: 'Cancel shipment SHP-001'*"
                )
            else:
                result = await get_shipment_status(db, shipment_no, org_id)
                if result:
                    response_text = (
                        f"⚠️ **Confirm Shipment Cancellation**\n\n"
                        f"You are about to cancel:\n"
                        f"- **Shipment:** {result.get('shipment_no')}\n"
                        f"- **Destination:** {result.get('destination')}\n"
                        f"- **Buyer:** {result.get('buyer', 'N/A')}\n"
                        f"- **Status:** {result.get('status')}\n\n"
                        f"This action **cannot be undone**. Please confirm."
                    )
                    pending = {"type": "cancel_shipment", "ref": shipment_no, "details": result}
                    requires_confirmation = True
                    data = result
                else:
                    response_text = (
                        f"Shipment **{shipment_no}** not found.\n\n"
                        f"*Say 'Show my shipments' to see available shipments.*"
                    )

        elif intent.intent == "delay_prediction":
            from app.services.production_service import get_delay_risks as _get_risks
            result = await _get_risks(db, org_id)
            data = result
            at_risk = result.get("at_risk", [])
            on_track = result.get("on_track", [])
            total = result.get("total_active", 0)
            if total == 0:
                response_text = (
                    "No active orders in production right now.\n\n"
                    "*Add or activate orders to see delay risk analysis.*"
                )
            elif not at_risk:
                track_lines = []
                for o in on_track[:5]:
                    bar = "█" * (o["progress_pct"] // 10) + "░" * (10 - o["progress_pct"] // 10)
                    track_lines.append(
                        f"- ✅ **{o['order_no']}** — {o['buyer']} · {o['status']} · `{bar}` {o['progress_pct']}%"
                    )
                response_text = (
                    f"✅ **All {total} active order{'s' if total!=1 else ''} are on track.**\n\n"
                    + ("\n".join(track_lines) if track_lines else "")
                    + "\n\n*No delivery risks detected at this time.*"
                )
            else:
                risk_icon = {"overdue": "🔴", "critical": "🟠", "warning": "🟡", "ok": "✅"}
                risk_lines = []
                for o in at_risk:
                    icon = risk_icon.get(o.get("risk", "ok"), "⚪")
                    days_str = (
                        f"**{abs(o['days_left'])} day{'s' if abs(o['days_left'])!=1 else ''} overdue**"
                        if o.get("days_left") is not None and o["days_left"] < 0
                        else f"{o['days_left']} day{'s' if o.get('days_left',1)!=1 else ''} left"
                        if o.get("days_left") is not None
                        else "no deadline set"
                    )
                    bar = "█" * (o["progress_pct"] // 10) + "░" * (10 - o["progress_pct"] // 10)
                    risk_lines.append(
                        f"- {icon} **{o['order_no']}** — {o['buyer']} · *{o['style']}*\n"
                        f"  Stage: {o['status']} · `{bar}` {o['progress_pct']}% · {days_str}"
                    )
                response_text = (
                    f"⚠️ **Delay Risk Report — {len(at_risk)} of {total} order{'s' if total!=1 else ''} at risk:**\n\n"
                    + "\n".join(risk_lines)
                    + (f"\n\n✅ {len(on_track)} order{'s' if len(on_track)!=1 else ''} on track." if on_track else "")
                )

        elif intent.intent == "create_invoice":
            order_id = _extract_order_ref(message, entities)
            if not order_id:
                response_text = (
                    "Which order should I create the invoice for?\n\n"
                    "*Example: 'Create invoice for PO-001'*"
                )
            else:
                result = await create_invoice(db, order_id, org_id, user_id)
                response_text = result.get("message", "Invoice created.")
                data = result

        elif intent.intent == "create_order":
            import json as _json
            # Accept all key variants GPT-4o might choose
            buyer = str(
                entities.get("buyer") or entities.get("buyer_name") or
                entities.get("client") or entities.get("customer") or ""
            ).strip()
            style = str(
                entities.get("style") or entities.get("style_name") or
                entities.get("product") or entities.get("product_name") or
                entities.get("garment") or entities.get("item") or ""
            ).strip()
            quantity = 0
            for _qk in ("quantity", "qty", "pieces", "units", "pcs", "number_of_pieces"):
                _qv = entities.get(_qk)
                if _qv:
                    try:
                        quantity = int(str(_qv).replace(",", ""))
                    except (ValueError, TypeError):
                        pass
                    break

            # Keyword/regex extraction fallback (entities empty when keyword-matched)
            if not buyer or not style or not quantity:
                _ext = _extract_create_order_entities(message, entities)
                buyer    = buyer    or str(_ext.get("buyer", "")).strip()
                style    = style    or str(_ext.get("style", "")).strip()
                quantity = quantity or int(_ext.get("quantity", 0) or 0)

            missing = []
            if not buyer:    missing.append("buyer name (e.g. H&M, Zara)")
            if not style:    missing.append("style / product name")
            if not quantity: missing.append("quantity in pieces")

            if missing:
                response_text = (
                    "To create a production order I need:\n\n"
                    + "\n".join(f"- ❌ **{m}**" for m in missing)
                    + "\n\n*Example: 'Create order for H&M, 5000 pieces of Summer Dress'*"
                )
            else:
                quantity = int(quantity)
                from app.services.production_service import get_next_order_no
                new_order_no = await get_next_order_no(db, org_id)
                pending_ref = _json.dumps({
                    "order_no": new_order_no, "buyer": buyer,
                    "style": style, "quantity": quantity,
                })
                response_text = (
                    f"📋 **Confirm New Production Order**\n\n"
                    f"- **Order No:** `{new_order_no}` *(auto-assigned)*\n"
                    f"- **Buyer:** {buyer}\n"
                    f"- **Style:** {style}\n"
                    f"- **Quantity:** {quantity:,} pcs\n"
                    f"- **Status:** Pending\n\n"
                    f"Confirm to create this order?"
                )
                pending = {"type": "create_order", "ref": pending_ref}
                requires_confirmation = True

        elif intent.intent == "book_shipment":
            import json as _json
            destination = str(entities.get("destination", "")).strip()
            carrier     = str(entities.get("carrier", "")).strip()
            order_no_shp = _extract_order_ref(message, entities)

            if not destination and not carrier:
                _ext = _extract_book_shipment_entities(message, entities)
                destination  = _ext.get("destination", "")
                carrier      = _ext.get("carrier", "")
                order_no_shp = order_no_shp or _ext.get("order_no")

            from app.services.shipment_service import get_next_shipment_no
            new_shp_no = await get_next_shipment_no(db, org_id)
            pending_ref = _json.dumps({
                "shipment_no": new_shp_no,
                "destination": destination or None,
                "carrier": carrier or None,
                "order_no": order_no_shp,
            })
            ord_line = f"\n- **Linked Order:** {order_no_shp}" if order_no_shp else ""
            response_text = (
                f"🚢 **Confirm New Shipment Booking**\n\n"
                f"- **Shipment No:** `{new_shp_no}` *(auto-assigned)*\n"
                f"- **Destination:** {destination or '*(not specified)*'}\n"
                f"- **Carrier:** {carrier or '*(not specified)*'}"
                + ord_line
                + f"\n- **Status:** Pending\n\n"
                f"Confirm to book this shipment?"
            )
            pending = {"type": "book_shipment", "ref": pending_ref}
            requires_confirmation = True

        elif intent.intent == "update_order_status":
            import json as _json
            _ext2 = _extract_update_status_entities(message, entities)
            order_ref_upd = _ext2.get("order_no")
            new_status    = _ext2.get("new_status")

            if not order_ref_upd:
                response_text = (
                    "Which order do you want to update? Please include the order number.\n\n"
                    "*Example: 'Move PO-001 to Cutting'*"
                )
            elif not new_status:
                response_text = (
                    f"What stage should **{order_ref_upd}** move to?\n\n"
                    f"Valid stages: {', '.join('**' + s + '**' for s in _VALID_STATUSES)}"
                )
            else:
                current = await get_order_status(db, order_ref_upd, org_id)
                if not current:
                    response_text = f"Order **{order_ref_upd}** not found."
                else:
                    pending_ref = _json.dumps({"order_no": order_ref_upd, "new_status": new_status})
                    response_text = (
                        f"🔄 **Confirm Status Update**\n\n"
                        f"- **Order:** {current.get('order_no')}\n"
                        f"- **Buyer:** {current.get('buyer')}\n"
                        f"- **Current Stage:** {current.get('status')}\n"
                        f"- **New Stage:** **{new_status}**\n\n"
                        f"Confirm to update?"
                    )
                    pending = {"type": "update_order_status", "ref": pending_ref}
                    requires_confirmation = True

        elif intent.intent == "log_quality":
            import json as _json
            _ext3 = _extract_log_quality_entities(message, entities)
            order_ref_q  = _ext3.get("order_no")
            defect_qty   = _ext3.get("defect_qty")
            defect_type  = _ext3.get("defect_type", "General")

            if not order_ref_q:
                response_text = (
                    "Which order are you logging defects for?\n\n"
                    "*Example: 'Log 30 defects for PO-001, type: stain'*"
                )
            elif not defect_qty:
                response_text = (
                    f"How many defects for **{order_ref_q}**?\n\n"
                    "*Example: 'Log 30 defects for PO-001'*"
                )
            else:
                defect_qty = int(defect_qty)
                current = await get_order_status(db, order_ref_q, org_id)
                if not current:
                    response_text = f"Order **{order_ref_q}** not found."
                else:
                    pending_ref = _json.dumps({
                        "order_no": order_ref_q,
                        "defect_qty": defect_qty,
                        "defect_type": str(defect_type),
                    })
                    response_text = (
                        f"⚠️ **Confirm Defect Log**\n\n"
                        f"- **Order:** {current.get('order_no')} — {current.get('buyer')}\n"
                        f"- **Defects to log:** {defect_qty:,} pieces\n"
                        f"- **Issue type:** {defect_type}\n\n"
                        f"Confirm to record this quality issue?"
                    )
                    pending = {"type": "log_quality", "ref": pending_ref}
                    requires_confirmation = True

        else:
            response_text = (
                f"I understood this is about **{intent.intent.replace('_', ' ')}** "
                f"but need more context. Could you give me more details?\n\n"
                f"*Say 'Help' to see everything I can do.*"
            )

    except Exception as e:
        response_text = f"I encountered an error processing your request: {str(e)}"

    return RouteResult(
        intent=intent.intent,
        confidence=intent.confidence,
        action_type="business_action",
        response=response_text,
        data=data,
        requires_confirmation=requires_confirmation,
        pending_action=pending,
    )


# ── Branch B — AI SQL Generation ──────────────────────────────────────────

async def _branch_sql(
    intent: IntentResult, message: str,
    user_id: int, org_id: int, db: AsyncSession
) -> RouteResult:
    """Generate safe SQL, execute it, and return NL summary."""
    try:
        from app.ai.sql_generator import generate_and_execute_sql
        result = await generate_and_execute_sql(message, intent, org_id, db)
        return RouteResult(
            intent=intent.intent,
            confidence=intent.confidence,
            action_type="analytics_question",
            response=result["summary"],
            data=result["rows"],
            sql_used=result["sql"],
        )
    except Exception as e:
        return RouteResult(
            intent=intent.intent,
            confidence=intent.confidence,
            action_type="analytics_question",
            response=f"I couldn't run that analytics query: {str(e)}",
            error=str(e),
        )


# ── Branch C — RAG / Knowledge base ──────────────────────────────────────

async def _branch_rag(
    intent: IntentResult, message: str, org_id: int,
    db: AsyncSession | None = None,
) -> RouteResult:
    """Search knowledge base and generate cited answer."""
    try:
        from app.ai.rag_service import query_knowledge_base
        result = await query_knowledge_base(message, org_id, db)
        return RouteResult(
            intent=intent.intent,
            confidence=intent.confidence,
            action_type="knowledge_question",
            response=result["answer"],
            sources=result["sources"],
        )
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "quota" in err_str.lower() or "insufficient_quota" in err_str:
            msg = (
                "📚 **Knowledge base search is temporarily unavailable.**\n\n"
                "Your OpenAI API key has reached its usage quota. "
                "Add credits at [platform.openai.com/account/billing](https://platform.openai.com/account/billing) "
                "then try again."
            )
        elif "authentication" in err_str.lower() or "api_key" in err_str.lower():
            msg = (
                "📚 **Knowledge base requires an OpenAI API key.**\n\n"
                "Add `OPENAI_API_KEY=sk-...` to `backend/.env` and restart the server."
            )
        else:
            msg = "📚 I couldn't search the knowledge base right now. Please try again in a moment."
        return RouteResult(
            intent=intent.intent,
            confidence=intent.confidence,
            action_type="knowledge_question",
            response=msg,
            error=err_str,
        )


# ── Branch V — Vision AI ──────────────────────────────────────────────────

async def _branch_vision(
    intent: IntentResult, message: str, image_url: str | None
) -> RouteResult:
    """Analyze image with GPT-4o Vision."""
    if not image_url:
        return RouteResult(
            intent=intent.intent,
            confidence=intent.confidence,
            action_type="vision_request",
            response="Please upload an image so I can analyze it for defects or labels.",
        )
    try:
        from app.ai.vision_service import analyze_image
        result = await analyze_image(image_url, message)
        return RouteResult(
            intent=intent.intent,
            confidence=intent.confidence,
            action_type="vision_request",
            response=result["summary"],
            data=result,
        )
    except Exception as e:
        return RouteResult(
            intent=intent.intent,
            confidence=intent.confidence,
            action_type="vision_request",
            response=f"Image analysis failed: {str(e)}",
            error=str(e),
        )


# ── Branch D — Clarification ──────────────────────────────────────────────

async def _branch_clarify(intent: IntentResult, message: str) -> RouteResult:
    """Friendly fallback — never leave the user stuck."""
    text = (
        "I didn't quite catch that. I'm a manufacturing AI — here are some things you can ask me:\n\n"
        "- *'Show my orders'* — see all production orders\n"
        "- *'What shipments are going out?'* — check shipments\n"
        "- *'Am I running low on any materials?'* — inventory check\n"
        "- *'How efficient is my production this week?'* — analytics\n"
        "- *'What's our quality policy?'* — document search\n\n"
        "Or just say **'Give me a summary'** for a full factory overview."
    )

    return RouteResult(
        intent=intent.intent,
        confidence=intent.confidence,
        action_type="unknown",
        response=text,
    )
