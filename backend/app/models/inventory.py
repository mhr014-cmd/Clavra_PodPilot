from sqlalchemy import Column, Integer, String
from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)

    material_code = Column(String, unique=True, nullable=False)
    material_name = Column(String, nullable=False)

    category = Column(String, nullable=False)

    unit = Column(String, nullable=False)

    stock_qty = Column(Integer, default=0)

    reserved_qty = Column(Integer, default=0)

    available_qty = Column(Integer, default=0)

    status = Column(String, default="In Stock")