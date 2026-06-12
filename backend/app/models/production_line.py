from sqlalchemy import Column, Integer, String

from app.database import Base


class ProductionLine(Base):

    __tablename__ = "production_lines"

    id = Column(Integer, primary_key=True, index=True)

    line_name = Column(String)

    supervisor = Column(String)

    status = Column(String)

    target_output = Column(Integer)

    actual_output = Column(Integer)

    efficiency = Column(Integer)

    defects = Column(Integer)

    operators = Column(Integer)