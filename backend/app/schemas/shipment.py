from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ShipmentCreate(BaseModel):
    shipment_no:      str
    order_id:         Optional[int]      = None   # link to production order
    buyer:            Optional[str]      = None
    destination:      Optional[str]      = None
    carrier:          Optional[str]      = None
    eta:              Optional[datetime] = None
    actual_departure: Optional[datetime] = None   # ship date


class ShipmentResponse(BaseModel):
    id:               int
    shipment_no:      str
    buyer:            Optional[str]      = None
    destination:      Optional[str]      = None
    carrier:          Optional[str]      = None
    status:           str
    eta:              Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    order_id:         Optional[int]      = None
    org_id:           Optional[int]      = None
    created_at:       Optional[datetime] = None
    # Enriched — joined from production_orders at API layer
    order_no:         Optional[str]      = None
    order_style:      Optional[str]      = None

    class Config:
        from_attributes = True
