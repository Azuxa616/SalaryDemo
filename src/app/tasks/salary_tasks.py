"""
薪资计算定时任务模块
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.app.core.celery_config import celery_app

from src.app.db.base import SessionLocal
from src.app.services.salary_calculation_service import SalaryCalculationService
from src.app.models.salary_engine import SalaryCalculationBatch

logger = logging.getLogger(__name__)


@celery_app.task(name="src.app.tasks.salary_tasks.check_scheduled_batches")
def check_scheduled_batches() -> dict:
	"""
	检查并执行到期的薪资计算批次
	每分钟执行一次，每分钟最多处理一个批次
	"""
	# 每次触发仅输出一次服务器时间（UTC）
	logger.info("⏱️ Scheduler tick (UTC): %s", datetime.now(timezone.utc).isoformat())
	
	db: Session = SessionLocal()
	try:
		service = SalaryCalculationService(db)
		
		# 查找状态为 PENDING/SCHEDULED 且到达执行时间的批次（使用数据库时间）
		scheduled_batch = db.query(SalaryCalculationBatch).filter(
			SalaryCalculationBatch.status.in_(['PENDING', 'SCHEDULED']),
			SalaryCalculationBatch.scheduled_time.isnot(None),
			SalaryCalculationBatch.scheduled_time <= func.now()
		).order_by(SalaryCalculationBatch.scheduled_time.asc()).first()
		
		if not scheduled_batch:
			logger.info("没有找到到期的薪资计算批次")
			return {
				"success": True,
				"message": "没有到期的批次",
				"processed": False
			}
		
		logger.info(f"找到到期批次: {scheduled_batch.id} ({scheduled_batch.batch_name})")
		
		# 执行批次计算
		success = service.execute_calculation_batch(scheduled_batch.id)
		
		if success:
			logger.info(f"批次 {scheduled_batch.id} 执行成功")
			return {
				"success": True,
				"message": f"批次 {scheduled_batch.id} 执行成功",
				"processed": True,
				"batch_id": str(scheduled_batch.id)
			}
		else:
			logger.error(f"批次 {scheduled_batch.id} 执行失败")
			return {
				"success": False,
				"message": f"批次 {scheduled_batch.id} 执行失败",
				"processed": True,
				"batch_id": str(scheduled_batch.id)
			}
			
	except Exception as e:
		logger.error(f"检查定时批次时发生错误: {str(e)}", exc_info=True)
		return {
			"success": False,
			"message": f"检查失败: {str(e)}",
			"processed": False,
			"error": str(e)
		}
	finally:
		db.close()


def get_batch_status(batch_id: UUID) -> Optional[dict]:
	"""获取批次状态"""
	db: Session = SessionLocal()
	try:
		batch = db.query(SalaryCalculationBatch).filter(
			SalaryCalculationBatch.id == batch_id
		).first()
		
		if not batch:
			return None
			
		return {
			"id": str(batch.id),
			"batch_name": batch.batch_name,
			"status": batch.status,
			"period_start": batch.period_start.isoformat() if batch.period_start else None,
			"period_end": batch.period_end.isoformat() if batch.period_end else None,
			"total_employees": batch.total_employees,
			"processed_count": batch.processed_count,
			"success_count": batch.success_count,
			"error_count": batch.error_count,
			"total_amount": float(batch.total_amount) if batch.total_amount else 0,
			"scheduled_time": batch.scheduled_time.isoformat() if batch.scheduled_time else None,
			"started_at": batch.started_at.isoformat() if batch.started_at else None,
			"completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
			"created_at": batch.created_at.isoformat() if batch.created_at else None
		}
		
	except Exception as e:
		logger.error(f"获取批次状态失败: {str(e)}", exc_info=True)
		return None
	finally:
		db.close()


def get_active_batches() -> list:
	"""获取所有活跃的批次"""
	db: Session = SessionLocal()
	try:
		batches = db.query(SalaryCalculationBatch).filter(
			SalaryCalculationBatch.status.in_(['PENDING', 'SCHEDULED', 'PROCESSING'])
		).order_by(SalaryCalculationBatch.created_at.desc()).all()
		return [
			{
				"id": str(batch.id),
				"batch_name": batch.batch_name,
				"status": batch.status,
				"period_start": batch.period_start.isoformat() if batch.period_start else None,
				"period_end": batch.period_end.isoformat() if batch.period_end else None,
				"scheduled_time": batch.scheduled_time.isoformat() if batch.scheduled_time else None,
				"created_at": batch.created_at.isoformat() if batch.created_at else None
			}
			for batch in batches
		]
		
	except Exception as e:
		logger.error(f"获取活跃批次失败: {str(e)}", exc_info=True)
		return []
	finally:
		db.close()
