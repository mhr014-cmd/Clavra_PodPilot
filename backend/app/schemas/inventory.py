from pydantic import BaseModel


class InventoryCreate(BaseModel):
    material_code: str
    material_name: str
    category: str
    unit: str
    stock_qty: int