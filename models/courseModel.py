from pydantic import BaseModel

class Course(BaseModel):
    course_code: int
    course_name: str