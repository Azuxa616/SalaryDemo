"""
定时任务调度器
使用 asyncio 实现，与 FastAPI 服务器集成
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import threading
import time

logger = logging.getLogger(__name__)


class SalaryScheduler:
    """薪资计算定时任务调度器"""
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    async def start(self):
        """启动定时任务调度器"""
        if self.is_running:
            logger.warning("定时任务调度器已经在运行")
            return
            
        logger.info("🚀 启动薪资计算定时任务调度器...")
        self.is_running = True
        self.stop_event.clear()
        
        # 在后台线程中运行调度器
        self.scheduler_thread = threading.Thread(
            target=self._run_scheduler_loop,
            daemon=True,
            name="SalaryScheduler"
        )
        self.scheduler_thread.start()
        
        logger.info("✅ 定时任务调度器启动成功")
        
    async def stop(self):
        """停止定时任务调度器"""
        if not self.is_running:
            return
            
        logger.info("🛑 正在停止定时任务调度器...")
        self.is_running = False
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
            
        logger.info("✅ 定时任务调度器已停止")
        
    def _run_scheduler_loop(self):
        """调度器主循环"""
        logger.info("⏰ 定时任务调度器开始运行，每分钟检查一次...")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # 执行定时任务
                self._execute_scheduled_tasks()
                
                # 等待到下一分钟
                self._wait_until_next_minute()
                
            except Exception as e:
                logger.error(f"定时任务调度器运行错误: {str(e)}", exc_info=True)
                # 出错后等待1分钟再继续
                time.sleep(60)
                
        logger.info("⏰ 定时任务调度器已退出")
        
    def _execute_scheduled_tasks(self):
        """执行定时任务"""
        try:
            from src.app.tasks.salary_tasks import check_scheduled_batches
            
            logger.debug("🔍 执行定时任务: 检查薪资计算批次...")
            result = check_scheduled_batches()
            
            if result.get("success"):
                if result.get("processed"):
                    logger.info(f"✅ 定时任务执行成功: {result.get('message')}")
                else:
                    logger.debug(f"ℹ️ 定时任务执行完成: {result.get('message')}")
            else:
                logger.error(f"❌ 定时任务执行失败: {result.get('message')}")
                
        except Exception as e:
            logger.error(f"执行定时任务时发生错误: {str(e)}", exc_info=True)
            
    def _wait_until_next_minute(self):
        """等待到下一分钟的开始"""
        now = datetime.now()
        # 计算到下一分钟开始的时间
        next_minute = now.replace(second=0, microsecond=0)
        if next_minute <= now:
            next_minute = next_minute.replace(minute=next_minute.minute + 1)
            
        # 等待时间（秒）
        wait_seconds = (next_minute - now).total_seconds()
        
        # 分段等待，每10秒检查一次停止信号
        while wait_seconds > 0 and not self.stop_event.is_set():
            sleep_time = min(10, wait_seconds)
            time.sleep(sleep_time)
            wait_seconds -= sleep_time
            
    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            "is_running": self.is_running,
            "thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False,
            "current_time": datetime.now(timezone.utc).isoformat()
        }


# 全局调度器实例
scheduler = SalaryScheduler()
