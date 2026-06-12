"""
Tool / Function Calling definitions — Clavra ProdPilot™
These are passed to OpenAI's function-calling API so the LLM can invoke
structured backend operations instead of generating free text.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "cancel_production_order",
            "description": "Cancel a production order by ID or order number. Requires manager permission.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_ref": {
                        "type": "string",
                        "description": "Order ID (numeric) or order number string e.g. PO-555"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for cancellation"
                    }
                },
                "required": ["order_ref"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_details",
            "description": "Get full details of a production order including status, quantities and buyer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_ref": {
                        "type": "string",
                        "description": "Order ID or order number"
                    }
                },
                "required": ["order_ref"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_last_orders",
            "description": "List the most recent production orders for this organisation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of orders to return (max 50)",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipment_status",
            "description": "Get the current status and ETA of a shipment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shipment_ref": {
                        "type": "string",
                        "description": "Shipment ID or shipment number e.g. SHP-1001"
                    }
                },
                "required": ["shipment_ref"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Check stock level for a material or inventory item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_ref": {
                        "type": "string",
                        "description": "Material code, name, or partial name"
                    }
                },
                "required": ["item_ref"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_quality_alert",
            "description": "Log a quality defect alert for a production line.",
            "parameters": {
                "type": "object",
                "properties": {
                    "line_id":      {"type": "integer", "description": "Production line ID"},
                    "defect_type":  {"type": "string",  "description": "Type of defect observed"},
                    "severity":     {"type": "string",  "enum": ["critical", "major", "minor"]},
                    "defect_count": {"type": "integer", "description": "Number of defective units"}
                },
                "required": ["line_id", "defect_type", "severity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_invoice",
            "description": "Trigger invoice generation for a completed production order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_ref": {
                        "type": "string",
                        "description": "Order number to generate invoice for"
                    }
                },
                "required": ["order_ref"]
            }
        }
    },
]

# Mapping from tool name → service function (populated at runtime via intent_router)
TOOL_HANDLER_MAP = {
    "cancel_production_order": "production_service.cancel_order",
    "get_order_details":       "production_service.get_order_status",
    "get_last_orders":         "production_service.get_last_orders",
    "get_shipment_status":     "shipment_service.get_shipment_status",
    "check_inventory":         "inventory_service.check_inventory",
    "create_invoice":          "production_service.create_invoice",
}
