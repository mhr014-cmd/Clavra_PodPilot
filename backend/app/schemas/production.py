from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProductionCreate(BaseModel):
    order_no:      str
    buyer:         str
    style:         str
    quantity:      int
    line_id:       Optional[int]      = None
    delivery_date: Optional[datetime] = None


class ProductionResponse(BaseModel):
    id:           int
    order_no:     str
    buyer:        str
    style:        str
    quantity:     int
    produced_qty: Optional[int]      = 0
    defect_qty:   Optional[int]      = 0
    status:       str
    line_id:      Optional[int]      = None
    delivery_date: Optional[datetime] = None
    org_id:       Optional[int]      = None
    created_at:   Optional[datetime] = None
    # Enriched — joined from shipments at API layer
    progress_pct:     Optional[int] = 0
    shipment_no:      Optional[str] = None
    shipment_id:      Optional[int] = None
    shipment_status:  Optional[str] = None

    class Config:
        from_attributes = True
