"""
薪资计算服务
实现薪资计算的核心逻辑
"""
import logging
from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.salary_engine import (
    SalaryRule, SalaryCalculationBatch, SalaryCalculationResult,
    EmployeeSalaryConfig, DeductionConfig
)
from app.models.worklog import WorkLog
from app.models.user import User
from app.services.rule_interpreter import RuleInterpreter

logger = logging.getLogger(__name__)


class SalaryCalculationService:
    """薪资计算服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.rule_interpreter = RuleInterpreter()
    
    def create_calculation_batch(
        self, 
        batch_name: str,
        period_start: date,
        period_end: date,
        calculation_period: str,
        created_by: int
    ) -> SalaryCalculationBatch:
        """创建计算批次"""
        try:
            batch = SalaryCalculationBatch(
                batch_name=batch_name,
                calculation_period=calculation_period,
                period_start=period_start,
                period_end=period_end,
                status='PENDING',
                created_by=created_by
            )
            
            self.db.add(batch)
            self.db.commit()
            self.db.refresh(batch)
            
            logger.info(f"创建计算批次成功: {batch.id}")
            return batch
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建计算批次失败: {str(e)}")
            raise
    
    def execute_calculation_batch(self, batch_id: UUID) -> bool:
        """执行计算批次"""
        batch = None
        try:
            batch = self.db.query(SalaryCalculationBatch).filter(
                SalaryCalculationBatch.id == batch_id
            ).first()
            
            if not batch:
                raise ValueError("计算批次不存在")
            
            if str(batch.status) != 'PENDING':
                raise ValueError(f"批次状态不正确: {batch.status}")
            
            # 更新状态为处理中
            batch.status = 'PROCESSING'
            batch.started_at = datetime.now(timezone.utc)
            self.db.commit()
            
            # 获取需要计算的员工列表
            period_start = batch.period_start
            period_end = batch.period_end
            employees = self._get_employees_for_calculation(period_start, period_end)
            batch.total_employees = len(employees)
            self.db.commit()
            
            success_count = 0
            error_count = 0
            total_amount = Decimal('0')
            
            # 逐个计算员工薪资
            for employee in employees:
                try:
                    employee_id = int(str(employee.id)) if hasattr(employee, 'id') and employee.id is not None else 0
                    result = self._calculate_employee_salary(
                        employee_id, 
                        period_start, 
                        period_end,
                        batch_id
                    )
                    
                    if result:
                        success_count += 1
                        total_amount += result.net_amount
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"员工 {employee.id} 薪资计算失败: {str(e)}")
                
                batch.processed_count += 1
                self.db.commit()
            
            # 更新批次状态
            batch.status = 'COMPLETED'
            batch.success_count = success_count
            batch.error_count = error_count
            batch.total_amount = total_amount
            batch.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(f"计算批次执行完成: {batch_id}, 成功: {success_count}, 失败: {error_count}")
            return True
            
        except Exception as e:
            if batch:
                batch.status = 'FAILED'
                batch.error_log = str(e)
                self.db.commit()
            
            logger.error(f"计算批次执行失败: {batch_id}, 错误: {str(e)}")
            return False
    
    def _get_employees_for_calculation(self, period_start: date, period_end: date) -> List[User]:
        """获取需要计算薪资的员工列表"""
        employees = self.db.query(User).join(WorkLog).filter(
            and_(
                WorkLog.date >= period_start,
                WorkLog.date <= period_end,
                WorkLog.status == 1
            )
        ).distinct().all()
        
        return employees
    
    def _calculate_employee_salary(
        self, 
        employee_id: int, 
        period_start: date, 
        period_end: date,
        batch_id: UUID
    ) -> Optional[SalaryCalculationResult]:
        """计算单个员工的薪资"""
        try:
            employee = self.db.query(User).filter(User.id == employee_id).first()
            if not employee:
                return None
            
            salary_config = self._get_employee_salary_config(employee_id, period_start)
            if not salary_config:
                logger.warning(f"员工 {employee_id} 没有薪资配置")
                return None
            
            worklogs = self._get_employee_worklogs(employee_id, period_start, period_end)
            
            total_hours = sum(w.hours for w in worklogs)
            overtime_hours = self._calculate_overtime_hours(worklogs, salary_config)
            
            rule_results = self._execute_salary_rules(
                employee, salary_config, worklogs, period_start, period_end
            )
            
            total_amount = sum(result['amount'] for result in rule_results.values())
            deductions = self._calculate_deductions(Decimal(str(total_amount)), employee, salary_config)
            net_amount = total_amount - sum(deductions.values())
            
            result = SalaryCalculationResult(
                batch_id=batch_id,
                employee_id=employee_id,
                period_start=period_start,
                period_end=period_end,
                base_salary=salary_config.base_salary,
                total_hours=total_hours,
                overtime_hours=overtime_hours,
                rule_results=rule_results,
                total_amount=total_amount,
                deductions=deductions,
                net_amount=net_amount,
                status='CALCULATED'
            )
            
            self.db.add(result)
            self.db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"员工 {employee_id} 薪资计算失败: {str(e)}")
            return None
    
    def _get_employee_salary_config(self, employee_id: int, effective_date: date) -> Optional[EmployeeSalaryConfig]:
        """获取员工薪资配置"""
        return self.db.query(EmployeeSalaryConfig).filter(
            and_(
                EmployeeSalaryConfig.employee_id == employee_id,
                EmployeeSalaryConfig.effective_from <= effective_date,
                EmployeeSalaryConfig.is_active == True,
                or_(
                    EmployeeSalaryConfig.effective_to.is_(None),
                    EmployeeSalaryConfig.effective_to >= effective_date
                )
            )
        ).order_by(EmployeeSalaryConfig.effective_from.desc()).first()
    
    def _get_employee_worklogs(self, employee_id: int, period_start: date, period_end: date) -> List[WorkLog]:
        """获取员工工作记录"""
        return self.db.query(WorkLog).filter(
            and_(
                WorkLog.employee_id == employee_id,
                WorkLog.date >= period_start,
                WorkLog.date <= period_end,
                WorkLog.status == 1
            )
        ).all()
    
    def _calculate_overtime_hours(self, worklogs: List[WorkLog], salary_config: EmployeeSalaryConfig) -> Decimal:
        """计算加班工时"""
        daily_limit = Decimal('8.0')
        overtime_hours = Decimal('0')
        
        for worklog in worklogs:
            worklog_hours = worklog.hours
            if worklog_hours is not None:
                try:
                    hours_decimal = Decimal(str(worklog_hours))
                    if hours_decimal > daily_limit:
                        overtime_hours += hours_decimal - daily_limit
                except (ValueError, TypeError):
                    continue
        
        return overtime_hours
    
    def _execute_salary_rules(
        self, 
        employee: User, 
        salary_config: EmployeeSalaryConfig, 
        worklogs: List[WorkLog],
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """执行薪资规则计算"""
        rules = self._get_active_salary_rules(period_start, period_end)
        context = self._build_calculation_context(employee, salary_config, worklogs)
        
        rule_results = {}
        
        # 按优先级排序规则
        sorted_rules = sorted(rules, key=lambda x: x.priority if x.priority else 0)
        
        for rule in sorted_rules:
            try:
                result = self.rule_interpreter.evaluate_rule(
                    {
                        'rule_type': rule.rule_type,
                        'formula': rule.formula,
                        'fixed_amount': rule.fixed_amount,
                        'conditions': rule.conditions,
                        'name': rule.name
                    },
                    context
                )
                
                rule_results[rule.name] = result
                
            except Exception as e:
                logger.error(f"规则 {rule.name} 执行失败: {str(e)}")
                rule_results[rule.name] = {
                    'amount': 0,
                    'error': str(e)
                }
        
        return rule_results
    
    def _get_active_salary_rules(self, period_start: date, period_end: date) -> List[SalaryRule]:
        """获取生效的薪资规则"""
        return self.db.query(SalaryRule).filter(
            and_(
                SalaryRule.is_active == True,
                SalaryRule.effective_from <= period_end,
                or_(
                    SalaryRule.effective_to.is_(None),
                    SalaryRule.effective_to >= period_start
                )
            )
        ).order_by(SalaryRule.priority).all()
    
    def _build_calculation_context(
        self, 
        employee: User, 
        salary_config: EmployeeSalaryConfig, 
        worklogs: List[WorkLog]
    ) -> Dict[str, Any]:
        """构建计算上下文"""
        total_hours = sum(w.hours for w in worklogs)
        overtime_hours = self._calculate_overtime_hours(worklogs, salary_config)
        
        context = {
            'employee': {
                'id': employee.id,
                'base_salary': salary_config.base_salary,
                'hourly_rate': salary_config.hourly_rate,
                'overtime_rate': salary_config.overtime_rate,
                'department_id': salary_config.department_id,
                'position': salary_config.position
            },
            'worklog': {
                'total_hours': total_hours,
                'overtime_hours': overtime_hours,
                'count': len(worklogs)
            }
        }
        
        for i, worklog in enumerate(worklogs):
            context[f'worklog_{i}'] = {
                'hours': worklog.hours,
                'task_type': worklog.task_type,
                'date': worklog.date
            }
        
        return context
    
    def _calculate_deductions(
        self, 
        total_amount: Decimal, 
        employee: User, 
        salary_config: EmployeeSalaryConfig
    ) -> Dict[str, Decimal]:
        """计算扣除项"""
        deductions = {}
        
        active_deductions = self.db.query(DeductionConfig).filter(
            and_(
                DeductionConfig.is_active == True,
                DeductionConfig.effective_from <= date.today()
            )
        ).all()
        
        for deduction in active_deductions:
            try:
                if deduction.deduction_type == 'PERCENTAGE':
                    if deduction.percentage is not None:
                        amount = total_amount * (deduction.percentage / 100)
                        if deduction.min_amount is not None:
                            amount = max(amount, deduction.min_amount)
                        if deduction.max_amount is not None:
                            amount = min(amount, deduction.max_amount)
                        deductions[deduction.name] = amount
                    else:
                        deductions[deduction.name] = Decimal('0')
                    
                elif deduction.deduction_type == 'FIXED':
                    deductions[deduction.name] = deduction.fixed_amount
                    
            except Exception as e:
                logger.error(f"扣除项 {deduction.name} 计算失败: {str(e)}")
                deductions[deduction.name] = Decimal('0')
        
        return deductions
    
    def get_calculation_batch(self, batch_id: UUID) -> Optional[SalaryCalculationBatch]:
        """获取计算批次"""
        return self.db.query(SalaryCalculationBatch).filter(
            SalaryCalculationBatch.id == batch_id
        ).first()
    
    def get_calculation_results(self, batch_id: UUID) -> List[SalaryCalculationResult]:
        """获取批次计算结果"""
        return self.db.query(SalaryCalculationResult).filter(
            SalaryCalculationResult.batch_id == batch_id
        ).all()
    
    def get_employee_salary_history(
        self, 
        employee_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[SalaryCalculationResult]:
        """获取员工薪资历史"""
        return self.db.query(SalaryCalculationResult).filter(
            and_(
                SalaryCalculationResult.employee_id == employee_id,
                SalaryCalculationResult.period_start >= start_date,
                SalaryCalculationResult.period_end <= end_date
            )
        ).order_by(SalaryCalculationResult.period_start.desc()).all()
