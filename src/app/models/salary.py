from pydantic import BaseModel

class SalaryResult(BaseModel):
    employee_id: int
    total_salary: float
    details: dict 