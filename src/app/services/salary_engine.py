from app.models.salary import SalaryResult

def calculate_salary(worklog):
    # TODO: 实现薪资计算逻辑
    return SalaryResult(
        employee_id=worklog.employee_id,
        total_salary=worklog.hours * 100,  # 示例：每小时100元
        details={"base": worklog.hours * 100}
    ) 
 