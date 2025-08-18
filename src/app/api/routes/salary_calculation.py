"""
薪资计算API路由（新文件）
- 立即计算：/salary-calculation/process-pending-worklogs
- 统一入口：/salary-calculation/calculate-salary
- 批次管理：/salary-calculation/calculation-batches 等
"""

from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, get_current_user
from app.core.roles import ROLE_ADMIN, ROLE_SUPERADMIN
from app.models.user import User
from app.models.salary_engine import SalaryCalculationBatch
from app.services.salary_calculation_service import SalaryCalculationService

router = APIRouter(prefix="/salary-calculation", tags=["salary-calculation"])


class SalaryCalculationRequest(BaseModel):
	"""薪资计算请求模型"""
	calculation_type: str = Field(..., description="计算类型：IMMEDIATE(立即计算) 或 SCHEDULED(定时计算)")
	scheduled_time: Optional[datetime] = Field(None, description="定时计算时间，立即计算时可为空")
	batch_name: Optional[str] = Field(None, description="批次名称，定时计算时必填")
	period_start: Optional[date] = Field(None, description="计算开始日期，为空则计算所有待核算记录")
	period_end: Optional[date] = Field(None, description="计算结束日期，为空则计算所有待核算记录")
	calculation_period: str = Field("CUSTOM", description="计算周期：MONTHLY/月度、WEEKLY/周度、CUSTOM/自定义")
	description: Optional[str] = Field(None, description="计算描述")


class SalaryCalculationResponse(BaseModel):
	"""薪资计算响应模型"""
	success: bool
	message: str
	calculation_id: Optional[str] = None
	batch_id: Optional[str] = None
	scheduled_time: Optional[datetime] = None
	data: Optional[dict] = None


@router.post("/process-pending-worklogs")
async def process_pending_worklogs(
	period_start: Optional[date] = Query(None, description="开始日期（可选）"),
	period_end: Optional[date] = Query(None, description="结束日期（可选）"),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""
	处理所有待核算的工作记录（快速结算未核算工时）
	"""
	if int(current_user.role) < ROLE_ADMIN:
		raise HTTPException(status_code=403, detail="权限不足：只有管理员及以上权限可以执行此操作")

	service = SalaryCalculationService(db)
	result = service.process_pending_worklogs(period_start=period_start, period_end=period_end)
	if result["success"]:
		return {
			"success": True,
			"message": result["message"],
			"data": {
				"processed_count": result["processed_count"],
				"success_count": result["success_count"],
				"error_count": result["error_count"],
				"processed_worklogs": result.get("processed_worklogs", []),
				"error_details": result.get("error_details", []),
			},
		}
	# 失败时也返回错误详情
	raise HTTPException(status_code=500, detail={
		"message": result.get("message", "处理失败"),
		"error_details": result.get("error_details", [])
	})


@router.post("/calculate-salary", response_model=SalaryCalculationResponse)
async def calculate_salary(
	request: SalaryCalculationRequest,
	db: Session = Depends(get_db),
	current_user: User = Depends(require_role(ROLE_ADMIN))
):
	"""
	计算薪资入口：
	- IMMEDIATE：立即处理待核算工时
	- SCHEDULED：创建定时批次
	"""
	service = SalaryCalculationService(db)

	if request.calculation_type == "IMMEDIATE":
		# 1) 为立即计算创建一个已完成状态的批次（按需求：状态为已执行）
		period_start = request.period_start or date.today()
		period_end = request.period_end or date.today()
		batch = service.create_calculation_batch(
			batch_name=f"IMMEDIATE-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
			calculation_period=request.calculation_period or "CUSTOM",
			period_start=period_start,
			period_end=period_end,
			created_by=current_user.id,
		)
		# 置为已执行并记录时间
		setattr(batch, "status", "COMPLETED")
		setattr(batch, "started_at", datetime.now())
		setattr(batch, "completed_at", datetime.now())
		db.commit()

		# 2) 执行计算并将结果写入该批次
		result = service.process_pending_worklogs(period_start=period_start, period_end=period_end, batch_id=batch.id)
		if result["success"]:
			# 回填批次统计
			setattr(batch, "processed_count", result["processed_count"])
			setattr(batch, "success_count", result["success_count"])
			setattr(batch, "error_count", result["error_count"])
			setattr(batch, "total_amount", result.get("total_amount", 0))
			db.commit()
			return SalaryCalculationResponse(
				success=True,
				message=result["message"],
				batch_id=str(batch.id),
				data={
					"processed_count": result["processed_count"],
					"success_count": result["success_count"],
					"error_count": result["error_count"],
					"processed_worklogs": result.get("processed_worklogs", []),
					"error_details": result.get("error_details", []),
				},
			)
		# 失败时也返回错误详情
		raise HTTPException(status_code=500, detail={
			"message": result.get("message", "计算失败"),
			"error_details": result.get("error_details", [])
		})

	if request.calculation_type == "SCHEDULED":
		if not request.scheduled_time:
			raise HTTPException(status_code=400, detail="定时计算必须指定计算时间")
		if not request.batch_name:
			raise HTTPException(status_code=400, detail="定时计算必须指定批次名称")
		if not request.period_start:
			request.period_start = date.today()
		if not request.period_end:
			request.period_end = date.today()

		batch = service.create_calculation_batch(
			batch_name=request.batch_name,
			calculation_period=request.calculation_period,
			period_start=request.period_start,
			period_end=request.period_end,
			created_by=current_user.id,
		)
		# 额外信息
		setattr(batch, "status", "SCHEDULED")
		setattr(batch, "scheduled_time", request.scheduled_time)
		setattr(batch, "description", request.description)
		db.commit()

		return SalaryCalculationResponse(
			success=True,
			message=f"定时计算批次创建成功，ID: {batch.id}",
			batch_id=str(batch.id),
			scheduled_time=request.scheduled_time,
		)

	raise HTTPException(status_code=400, detail="无效的计算类型，必须是 IMMEDIATE 或 SCHEDULED")


@router.get("/calculation-batches", response_model=List[dict])
async def get_calculation_batches(
	status: Optional[str] = Query(None, description="批次状态筛选"),
	skip: int = Query(0, ge=0, description="跳过记录数"),
	limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
	db: Session = Depends(get_db),
	current_user: User = Depends(require_role(ROLE_ADMIN))
):
	"""获取薪资计算批次列表"""
	query = db.query(SalaryCalculationBatch)
	if status:
		query = query.filter(SalaryCalculationBatch.status == status)
	batches = query.order_by(SalaryCalculationBatch.created_at.desc()).offset(skip).limit(limit).all()

	result = []
	for batch in batches:
		result.append({
			"id": str(batch.id),
			"batch_name": batch.batch_name,
			"calculation_period": batch.calculation_period,
			"period_start": batch.period_start,
			"period_end": batch.period_end,
			"status": batch.status,
			"scheduled_time": getattr(batch, "scheduled_time", None),
			"total_employees": batch.total_employees,
			"processed_count": batch.processed_count,
			"success_count": batch.success_count,
			"error_count": batch.error_count,
			"total_amount": float(batch.total_amount) if batch.total_amount else 0,
			"created_at": batch.created_at,
			"started_at": batch.started_at,
			"completed_at": batch.completed_at,
			"description": getattr(batch, "description", None),
		})
	return result


@router.post("/execute-scheduled-batch/{batch_id}")
async def execute_scheduled_batch(
	batch_id: str,
	db: Session = Depends(get_db),
	current_user: User = Depends(require_role(ROLE_ADMIN))
):
	"""执行定时计算批次"""
	service = SalaryCalculationService(db)
	batch = service.get_calculation_batch(UUID(batch_id))
	if not batch:
		raise HTTPException(status_code=404, detail="计算批次不存在")
	if batch.status != "SCHEDULED":
		raise HTTPException(status_code=400, detail=f"批次状态不正确: {batch.status}")

	success = service.execute_calculation_batch(UUID(batch_id))
	if success:
		return {"success": True, "message": f"批次 {batch_id} 执行成功", "batch_id": batch_id}
	raise HTTPException(status_code=500, detail=f"批次 {batch_id} 执行失败")


@router.delete("/calculation-batch/{batch_id}")
async def delete_calculation_batch(
	batch_id: str,
	db: Session = Depends(get_db),
	current_user: User = Depends(require_role(ROLE_SUPERADMIN))
):
	"""删除计算批次（仅超级管理员）"""
	batch = db.query(SalaryCalculationBatch).filter(SalaryCalculationBatch.id == batch_id).first()
	if not batch:
		raise HTTPException(status_code=404, detail="计算批次不存在")
	if batch.status not in ["SCHEDULED", "CANCELLED"]:
		raise HTTPException(status_code=400, detail="只能删除待执行或已取消的批次")
	db.delete(batch)
	db.commit()
	return {"success": True, "message": f"批次 {batch_id} 删除成功"}
