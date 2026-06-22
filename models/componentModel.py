from pydantic import BaseModel

class Component(BaseModel):
    component_type: str
    Weightage: float
    Total_marks: float
    Obtained_marks: float