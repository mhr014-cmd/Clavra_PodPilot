from pydantic import BaseModel


class ProductionLineCreate(BaseModel):

    line_name: str

    supervisor: str

    target_output: int

    operators: int