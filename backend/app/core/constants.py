"""App-wide constants for Clavra ProdPilot™."""

# ── App identity ──────────────────────────────────────────────────────────
APP_NAME    = "Clavra ProdPilot™"
APP_VERSION = "2.0.0"
APP_COMPANY = "Clavra"

# ── Production order statuses ─────────────────────────────────────────────
ORDER_STATUSES = [
    "Pending", "Cutting", "Sewing", "Finishing",
    "Packing", "Completed", "Cancelled", "On Hold"
]

# ── Shipment statuses ─────────────────────────────────────────────────────
SHIPMENT_STATUSES = [
    "Pending", "In Transit", "Customs", "Delivered",
    "Delayed", "Cancelled"
]

# ── Inventory statuses ────────────────────────────────────────────────────
INVENTORY_STATUSES = ["In Stock", "Low Stock", "Out of Stock", "Reserved"]

# ── AI intent action types ────────────────────────────────────────────────
ACTION_TYPE_BUSINESS   = "business_action"
ACTION_TYPE_ANALYTICS  = "analytics_question"
ACTION_TYPE_KNOWLEDGE  = "knowledge_question"
ACTION_TYPE_VISION     = "vision_request"
ACTION_TYPE_UNKNOWN    = "unknown"

# ── AI intent names ───────────────────────────────────────────────────────
KNOWN_INTENTS = [
    "cancel_order", "get_order_status", "get_last_orders",
    "count_orders", "production_efficiency", "shipment_status",
    "delay_prediction", "inventory_check", "defect_analysis",
    "ask_policy", "ask_manual", "create_invoice",
    "quality_report", "unknown"
]

# ── SQL safety ────────────────────────────────────────────────────────────
SQL_ALLOWED_TABLES = {
    "production_orders", "shipments", "inventory",
    "production_lines", "quality_reports",
    "planning_tna", "organizations"
}
SQL_FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "CREATE", "GRANT", "REVOKE", "EXEC"
]

# ── File upload ───────────────────────────────────────────────────────────
ALLOWED_PDF_TYPES  = ["application/pdf"]
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# ── Cookie names ──────────────────────────────────────────────────────────
REFRESH_TOKEN_COOKIE = "refresh_token"

# ── Redis key prefixes ────────────────────────────────────────────────────
REDIS_BLACKLIST_PREFIX = "blacklist:"
REDIS_RATE_LIMIT_PREFIX = "rate:"
REDIS_CHAT_PREFIX = "chat:"
