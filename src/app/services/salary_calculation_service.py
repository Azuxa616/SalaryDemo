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

from src.app.models.salary_engine import (
    SalaryRule, SalaryCalculationBatch, SalaryCalculationResult,
    EmployeeSalaryConfig, DeductionConfig
)
from src.app.models.worklog import WorkLog
from src.app.models.user import User
from src.app.services.rule_interpreter import RuleInterpreter

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
            
            # 复用“立即计算”的逐条工作记录处理逻辑，确保规则上下文包含 worklog.hours 等字段
            period_start = batch.period_start
            period_end = batch.period_end
            process_result = self.process_pending_worklogs(period_start=period_start, period_end=period_end, batch_id=batch_id)

            # 根据处理结果回填批次统计
            batch.processed_count = int(process_result.get("processed_count", 0))
            batch.success_count = int(process_result.get("success_count", 0))
            batch.error_count = int(process_result.get("error_count", 0))
            try:
                batch.total_amount = Decimal(str(process_result.get("total_amount", 0)))
            except Exception:
                batch.total_amount = Decimal('0')

            # 统计涉及员工数（可选，避免额外查询时，可从已处理记录推断）
            try:
                employees_involved = {int(item.get("employee_id")) for item in process_result.get("processed_worklogs", []) if item.get("employee_id") is not None}
                batch.total_employees = len(employees_involved)
            except Exception:
                pass

            # 更新批次状态
            if process_result.get("success"):
                batch.status = 'COMPLETED'
            else:
                batch.status = 'FAILED'
                batch.error_log = process_result.get("message", "")
            batch.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(
                f"计算批次执行完成: {batch_id}, 成功: {batch.success_count}, 失败: {batch.error_count}"
            )
            return bool(process_result.get("success"))
            
        except Exception as e:
            if batch:
                batch.status = 'FAILED'
                batch.error_log = str(e)
                self.db.commit()
            
            logger.error(f"计算批次执行失败: {batch_id}, 错误: {str(e)}")
            return False
    
    def process_pending_worklogs(self, period_start: Optional[date] = None, period_end: Optional[date] = None, *, batch_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        处理所有待核算的工作记录
        实现功能1-4：检查未核算记录、检查薪资设置、计算薪资、更新状态、保存结果
        """
        try:
            # 1. 检查数据库中的所有工作记录，筛选其中status为0（未核算）的记录
            pending_worklogs = self._get_pending_worklogs(period_start, period_end)
            
            if not pending_worklogs:
                logger.info("没有找到待核算的工作记录")
                return {
                    "success": True,
                    "message": "没有待核算的工作记录",
                    "processed_count": 0,
                    "success_count": 0,
                    "error_count": 0
                }
            
            logger.info(f"找到 {len(pending_worklogs)} 条待核算的工作记录")
            
            success_count = 0
            error_count = 0
            processed_worklogs = []
            error_details = []
            
            # 2. 对于每一条上述的记录，根据其员工id检查数据库中相关员工的薪资设置
            for worklog in pending_worklogs:
                try:
                    logger.debug(
                        "准备处理工作记录: id=%s, employee_id=%s, date=%s (type=%s), status=%s, hours=%s, task_type=%s",
                        getattr(worklog, 'entry_id', None),
                        getattr(worklog, 'employee_id', None),
                        getattr(worklog, 'date', None),
                        type(getattr(worklog, 'date', None)).__name__ if hasattr(worklog, 'date') else None,
                        getattr(worklog, 'status', None),
                        getattr(worklog, 'hours', None),
                        getattr(worklog, 'task_type', None)
                    )

                    # 检查员工薪资配置
                    employee_id = int(str(worklog.employee_id))
                    worklog_date = self._ensure_date(worklog.date)
                    logger.debug("归一化工作记录日期: raw=%s -> normalized=%s", worklog.date, worklog_date)
                    salary_config = self._get_employee_salary_config(employee_id, worklog_date)
                    if not salary_config:
                        logger.warning(f"员工 {worklog.employee_id} 在 {worklog_date} 没有有效的薪资配置")
                        error_count += 1
                        error_details.append({
                            "worklog_id": str(getattr(worklog, 'entry_id', None)),
                            "employee_id": employee_id,
                            "date": worklog_date,
                            "step": "check_salary_config",
                            "error": f"员工 {worklog.employee_id} 在 {worklog_date} 没有有效的薪资配置"
                        })
                        continue
                    # 打印本次将使用的薪资设置摘要
                    logger.debug("使用薪资设置: %s", self._summarize_salary_config(salary_config))
                    
                    # 3. 使用已启用的薪资规则计算该条工作记录的薪资
                    calculation_result = self._calculate_single_worklog_salary(worklog, salary_config)
                    
                    if calculation_result:
                        # 4. 输出计算结果到计算结果表（若提供了批次则写入该批次）
                        self._save_worklog_calculation_result(worklog, calculation_result, salary_config, batch_id=batch_id)
                        
                        # 更新工作记录状态为已核算(1)
                        setattr(worklog, 'status', 1)
                        self.db.commit()
                        
                        success_count += 1
                        processed_worklogs.append({
                            "worklog_id": str(worklog.entry_id),
                            "employee_id": employee_id,
                            "date": worklog_date,
                            "calculated_amount": float(calculation_result['total_amount'])
                        })
                        
                        logger.info(f"工作记录 {worklog.entry_id} 薪资计算成功: {calculation_result['total_amount']}")
                    else:
                        error_count += 1
                        logger.error(f"工作记录 {worklog.entry_id} 薪资计算失败")
                        error_details.append({
                            "worklog_id": str(getattr(worklog, 'entry_id', None)),
                            "employee_id": employee_id,
                            "date": worklog_date,
                            "step": "calculate_worklog",
                            "error": "薪资计算失败"
                        })
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理工作记录 {worklog.entry_id} 时发生错误: {str(e)}", exc_info=True)
                    # 发生异常时回滚，避免会话进入 PendingRollback 状态影响后续处理
                    try:
                        self.db.rollback()
                    except Exception:
                        logger.debug("rollback时发生附加异常，忽略", exc_info=True)
                    error_details.append({
                        "worklog_id": str(getattr(worklog, 'entry_id', None)),
                        "employee_id": employee_id if 'employee_id' in locals() else getattr(worklog, 'employee_id', None),
                        "date": worklog_date if 'worklog_date' in locals() else self._ensure_date(getattr(worklog, 'date', date.today())),
                        "step": "process_worklog",
                        "error": str(e),
                        "exception_type": type(e).__name__
                    })
                    continue
            
            # 提交所有更改
            self.db.commit()
            
            # 汇总本次总金额
            try:
                total_amount_sum = sum(Decimal(str(item.get("calculated_amount", 0))) for item in processed_worklogs)
            except Exception:
                total_amount_sum = Decimal('0')

            result = {
                "success": True,
                "message": f"处理完成，成功: {success_count}, 失败: {error_count}",
                "processed_count": len(pending_worklogs),
                "success_count": success_count,
                "error_count": error_count,
                "processed_worklogs": processed_worklogs,
                "total_amount": float(total_amount_sum),
                "error_details": error_details
            }
            
            logger.info(f"工作记录处理完成: {result}")
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"处理待核算工作记录失败: {str(e)}")
            return {
                "success": False,
                "message": f"处理失败: {str(e)}",
                "processed_count": 0,
                "success_count": 0,
                "error_count": 0,
                "processed_worklogs": [],
                "error_details": [
                    {
                        "step": "process_pending_worklogs",
                        "error": str(e),
                        "exception_type": type(e).__name__
                    }
                ]
            }
    
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
            
            total_amount = sum(Decimal(str(result['amount'])) for result in rule_results.values())
            deductions = self._calculate_deductions(Decimal(str(total_amount)), employee, salary_config)
            net_amount = total_amount - sum(deductions.values())
            total_amount = Decimal(str(total_amount)).quantize(Decimal('0.01'))
            net_amount = Decimal(str(net_amount)).quantize(Decimal('0.01'))
            
            result = SalaryCalculationResult(
                batch_id=batch_id,
                employee_id=employee_id,
                period_start=period_start,
                period_end=period_end,
                base_salary=salary_config.base_salary,
                total_hours=total_hours,
                overtime_hours=overtime_hours,
                rule_results=self._to_json_safe(rule_results),
                total_amount=Decimal(str(total_amount)),
                deductions=self._to_json_safe(deductions),
                net_amount=Decimal(str(net_amount)),
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
        logger.debug(
            "查找薪资配置: employee_id=%s, effective_date=%s, 条件: effective_from<=date 且 (effective_to为空或>=date) 且 is_active=True",
            employee_id, effective_date
        )
        query = self.db.query(EmployeeSalaryConfig).filter(
            and_(
                EmployeeSalaryConfig.employee_id == employee_id,
                EmployeeSalaryConfig.effective_from <= effective_date,
                or_(
                    EmployeeSalaryConfig.is_active == True,
                    EmployeeSalaryConfig.is_active.is_(None)
                ),
                or_(
                    EmployeeSalaryConfig.effective_to.is_(None),
                    EmployeeSalaryConfig.effective_to >= effective_date
                )
            )
        ).order_by(EmployeeSalaryConfig.effective_from.desc())

        config = query.first()

        if config:
            cond1 = config.effective_from <= effective_date
            cond2a = (config.effective_to is None)
            cond2b = (config.effective_to is not None and config.effective_to >= effective_date)
            cond2 = cond2a or cond2b
            cond3 = (config.is_active is True) or (config.is_active is None)
            logger.debug(
                "命中配置: %s; 比较明细 => effective_from(%s) <= effective_date(%s): %s; "
                "(effective_to is None: %s) or (effective_to(%s) >= effective_date(%s): %s): %s; is_active: %s; 综合: %s",
                self._summarize_salary_config(config),
                config.effective_from, effective_date, cond1,
                cond2a, config.effective_to, effective_date, (config.effective_to >= effective_date) if config.effective_to is not None else None, cond2,
                config.is_active, (cond1 and cond2 and cond3)
            )
            return config

        # 未命中时输出该员工所有配置，帮助诊断
        candidates = self.db.query(EmployeeSalaryConfig).filter(
            EmployeeSalaryConfig.employee_id == employee_id
        ).order_by(EmployeeSalaryConfig.effective_from.desc()).all()
        logger.debug(
            "未命中配置，员工 %s 现有配置共 %d 条: %s",
            employee_id, len(candidates), [self._summarize_salary_config(c) for c in candidates]
        )
        return None
    
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
    
    def _get_pending_worklogs(self, period_start: Optional[date] = None, period_end: Optional[date] = None) -> List[WorkLog]:
        """获取所有待核算(status=0)的工作记录"""
        query = self.db.query(WorkLog).filter(WorkLog.status == 0)
        
        if period_start:
            query = query.filter(WorkLog.date >= period_start)
        if period_end:
            query = query.filter(WorkLog.date <= period_end)
        
        return query.order_by(WorkLog.date, WorkLog.created_at).all()
    
    def _calculate_single_worklog_salary(self, worklog: WorkLog, salary_config: EmployeeSalaryConfig) -> Optional[Dict[str, Any]]:
        """计算单条工作记录的薪资"""
        try:
            # 获取员工信息
            employee = self.db.query(User).filter(User.id == worklog.employee_id).first()
            if not employee:
                logger.error(f"员工 {worklog.employee_id} 不存在")
                return None
            
            # 构建计算上下文
            context = self._build_single_worklog_context(worklog, employee, salary_config)
            
            # 获取生效的薪资规则
            worklog_date = self._ensure_date(worklog.date)
            logger.debug("获取薪资规则使用日期: %s (from raw=%s)", worklog_date, worklog.date)
            rules = self._get_active_salary_rules(worklog_date, worklog_date)
            
            if not rules:
                logger.warning(f"在 {worklog_date} 没有找到生效的薪资规则")
                return None
            
            # 执行薪资规则计算
            rule_results = {}
            total_amount = Decimal('0')
            
            # 按优先级排序规则
            sorted_rules = sorted(rules, key=lambda x: x.priority if x.priority else 0)
            # 打印规则摘要
            logger.debug("使用薪资规则(%d 条): %s", len(sorted_rules), self._summarize_rules(sorted_rules))
            
            for rule in sorted_rules:
                try:
                    result = self.rule_interpreter.evaluate_rule(
                        {
                            'rule_type': rule.rule_type,
                            'formula': rule.formula,
                            'variables': getattr(rule, 'variables', None),
                            'fixed_amount': rule.fixed_amount,
                            'conditions': rule.conditions,
                            'name': rule.name
                        },
                        context
                    )
                    
                    rule_results[rule.name] = result
                    
                    # 累加金额
                    if 'amount' in result and result['amount']:
                        try:
                            amount = Decimal(str(result['amount']))
                            total_amount += amount
                        except (ValueError, TypeError):
                            logger.warning(f"规则 {rule.name} 金额无效: {result['amount']}")
                    
                except Exception as e:
                    logger.error(f"规则 {rule.name} 执行失败: {str(e)}")
                    rule_results[rule.name] = {
                        'amount': 0,
                        'error': str(e)
                    }
            
            # 取消扣除项计算：仅保留 worklog + 薪资配置 + 规则计算单元
            deductions = {}
            net_amount = total_amount
            
            return {
                'total_amount': self._to_json_safe(total_amount),
                'net_amount': self._to_json_safe(net_amount),
                'rule_results': self._to_json_safe(rule_results),
                'deductions': self._to_json_safe(deductions),
                'worklog_hours': self._to_json_safe(Decimal(str(worklog.hours)).quantize(Decimal('0.01')) if worklog.hours is not None else Decimal('0.00')),
                'base_salary': self._to_json_safe(Decimal(str(salary_config.base_salary)).quantize(Decimal('0.01'))),
                'hourly_rate': self._to_json_safe(Decimal(str(salary_config.hourly_rate)).quantize(Decimal('0.01')))
            }
            
        except Exception as e:
            logger.error(f"计算工作记录薪资失败: {str(e)}", exc_info=True)
            return None
    
    def _build_single_worklog_context(self, worklog: WorkLog, employee: User, salary_config: EmployeeSalaryConfig) -> Dict[str, Any]:
        """构建单条工作记录的计算上下文"""
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
                'hours': worklog.hours,
                'task_type': worklog.task_type,
                'date': worklog.date,
                'project_id': worklog.project_id,
                'remarks': worklog.remarks
            }
        }
        
        # 添加项目相关信息（如果需要）
        if hasattr(worklog, 'project') and worklog.project:
            context['project'] = {
                'id': worklog.project.id,
                'name': worklog.project.name,
                'type': getattr(worklog.project, 'type', '')
            }
        
        return context
    
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
                        'variables': getattr(rule, 'variables', None),
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
    
    def _calculate_deductions_for_worklog(self, total_amount: Decimal, employee: User, salary_config: EmployeeSalaryConfig) -> Dict[str, Decimal]:
        """为单条工作记录计算扣除项"""
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
    
    def _save_worklog_calculation_result(self, worklog: WorkLog, calculation_result: Dict[str, Any], salary_config: EmployeeSalaryConfig, *, batch_id: Optional[UUID] = None):
        """保存工作记录的计算结果到计算结果表"""
        try:
            worklog_date = self._ensure_date(worklog.date)
            logger.debug(
                "保存计算结果: worklog_id=%s, employee_id=%s, date=%s (type=%s), total=%s, net=%s",
                getattr(worklog, 'entry_id', None),
                getattr(worklog, 'employee_id', None),
                worklog_date,
                type(worklog_date).__name__,
                calculation_result.get('total_amount'),
                calculation_result.get('net_amount')
            )
            # 检查是否已存在该工作记录的计算结果
            existing_result = self.db.query(SalaryCalculationResult).filter(
                and_(
                    SalaryCalculationResult.employee_id == worklog.employee_id,
                    SalaryCalculationResult.period_start == worklog_date,
                    SalaryCalculationResult.period_end == worklog_date
                )
            ).first()
            
            if existing_result:
                # 更新现有结果
                existing_result.total_hours = self._to_json_safe(worklog.hours)
                existing_result.rule_results.update(self._to_json_safe(calculation_result['rule_results']))
                existing_result.total_amount += Decimal(str(calculation_result['total_amount']))
                existing_result.deductions.update(self._to_json_safe(calculation_result['deductions']))
                existing_result.net_amount += Decimal(str(calculation_result['net_amount']))
                existing_result.updated_at = datetime.now(timezone.utc)
                logger.info(f"更新工作记录 {worklog.entry_id} 的计算结果")
            else:
                # 若提供了批次ID，则插入新记录；否则跳过
                if batch_id is None:
                    logger.debug(
                        "跳过插入新计算结果（无批次上下文）: worklog_id=%s, employee_id=%s, date=%s",
                        getattr(worklog, 'entry_id', None), worklog.employee_id, worklog_date
                    )
                else:
                    result = SalaryCalculationResult(
                        batch_id=batch_id,
                        employee_id=worklog.employee_id,
                        period_start=worklog_date,
                        period_end=worklog_date,
                        base_salary=salary_config.base_salary,
                        total_hours=self._to_json_safe(worklog.hours),
                        overtime_hours=Decimal('0'),
                        rule_results=self._to_json_safe(calculation_result['rule_results']),
                        total_amount=Decimal(str(calculation_result['total_amount'])),
                        deductions=self._to_json_safe(calculation_result['deductions']),
                        net_amount=Decimal(str(calculation_result['net_amount'])),
                        status='CALCULATED',
                        notes=f"单条工作记录计算: {worklog.task_type}"
                    )
                    self.db.add(result)
                    logger.info(f"保存工作记录 {worklog.entry_id} 的计算结果到批次 {batch_id}")
            
        except Exception as e:
            logger.error(f"保存工作记录计算结果失败: {str(e)}", exc_info=True)
            raise

    def _to_json_safe(self, value: Any) -> Any:
        """将包含 Decimal、date、datetime 等对象的结构递归转换为可 JSON 序列化的安全类型。
        - Decimal -> float
        - date/datetime -> isoformat 字符串
        - dict/list/tuple -> 递归处理
        其余类型原样返回。
        """
        try:
            if isinstance(value, Decimal):
                return float(value)
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, date):
                return value.isoformat()
            if isinstance(value, dict):
                return {k: self._to_json_safe(v) for k, v in value.items()}
            if isinstance(value, list):
                return [self._to_json_safe(v) for v in value]
            if isinstance(value, tuple):
                return [self._to_json_safe(v) for v in value]
            return value
        except Exception:
            logger.debug("_to_json_safe 转换失败，返回字符串: %s", value, exc_info=True)
            return str(value)

    def _ensure_date(self, value) -> date:
        """将输入值安全转换为 date 类型。

        - datetime -> datetime.date
        - date -> 原样返回
        - 其他 -> 尝试解析为 ISO 字符串日期，失败则记录警告并返回今天
        """
        try:
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            # 兜底解析字符串
            return datetime.fromisoformat(str(value)).date()
        except Exception:
            logger.warning("无法解析日期值: %s (type=%s)，回退为今天", value, type(value).__name__, exc_info=True)
            return date.today()

    def _summarize_salary_config(self, config: EmployeeSalaryConfig) -> str:
        """格式化输出薪资设置关键信息用于调试日志"""
        try:
            return (
                f"employee_id={config.employee_id}, base_salary={config.base_salary}, "
                f"hourly_rate={config.hourly_rate}, overtime_rate={config.overtime_rate}, "
                f"department_id={getattr(config, 'department_id', None)}, position={getattr(config, 'position', None)}, "
                f"effective_from={getattr(config, 'effective_from', None)}, effective_to={getattr(config, 'effective_to', None)}, "
                f"is_active={getattr(config, 'is_active', None)}"
            )
        except Exception as e:
            logger.warning("格式化薪资设置摘要失败: %s", str(e), exc_info=True)
            return "<salary_config_summary_error>"

    def _summarize_rules(self, rules: List[SalaryRule]) -> str:
        """格式化输出规则列表关键信息用于调试日志"""
        try:
            parts = []
            for r in rules:
                parts.append(
                    f"[name={getattr(r,'name',None)}, type={getattr(r,'rule_type',None)}, priority={getattr(r,'priority',None)}, "
                    f"effective=({getattr(r,'effective_from',None)}..{getattr(r,'effective_to',None)}), active={getattr(r,'is_active',None)}]"
                )
            return ", ".join(parts)
        except Exception as e:
            logger.warning("格式化薪资规则摘要失败: %s", str(e), exc_info=True)
            return "<rules_summary_error>"
    
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
