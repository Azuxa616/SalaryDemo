# 定时任务模块使用说明（Scheduled Tasks）

## 概述

本模块用于按计划自动执行薪资计算批次。设计目标：
- 批次创建时仅入库为 PENDING，并记录 `scheduled_time`（UTC）。
- 定时器每分钟检查是否有到期批次并触发计算。
- 计算路径与“立即计算”完全一致，避免上下文差异导致的规则变量缺失问题。

当前实现同时支持两种触发方式：
- Celery Beat（推荐）：通过 `celery beat` 每分钟触发一次 `check_scheduled_batches` 任务。
- 线程调度器：应用启动时的后台线程也会每分钟调用一次检查逻辑（适合开发/无 Celery 时）。

## 关键组件

- 任务函数：`src/app/tasks/salary_tasks.py` 的 `check_scheduled_batches`
  - 已注册为 Celery 任务：`@celery_app.task(name="src.app.tasks.salary_tasks.check_scheduled_batches")`
  - 每次触发时日志输出服务器时间（UTC），并从数据库按 `func.now()` 查找到期批次
  - 命中后调用服务层执行计算

- 服务层：`src/app/services/salary_calculation_service.py`
  - `execute_calculation_batch(batch_id)`：定时批次的执行入口
  - 已改为复用 `process_pending_worklogs(...)` 的逐条工作记录处理逻辑
    - 确保规则上下文包含 `worklog.hours` 等字段，避免 `hourly_rate * hours` 的 `hours 未定义` 问题
    - 处理完成后回填统计字段（processed_count、success_count、error_count、total_amount、total_employees）并更新状态

- Celery 配置：`src/app/core/celery_config.py`
  - 队列 `salary_calculation`
  - 定时任务：`beat_schedule` 每分钟触发一次 `check_scheduled_batches`
  - 时区：统一使用 `UTC`

- 线程调度器：`src/app/core/scheduler.py`
  - 应用生命周期内的后台线程，每分钟主动调用一次 `check_scheduled_batches()`（非 Celery 方式）

## 工作流程

1) 创建定时批次（SCHEDULED）
- 接口：`POST /salary-calculation/calculate-salary`，`calculation_type = "SCHEDULED"`
- 后端会把前端传入的 `scheduled_time` 标准化为 UTC 存入数据库：
  - 若带时区（Z 或 +08:00），直接转为 UTC
  - 若不带时区，按 `Asia/Shanghai` 解释，再转为 UTC
- 批次状态保持为 `PENDING`（不再使用 `SCHEDULED`），并记录 `scheduled_time`

2) 周期检查与执行
- 每分钟由 Celery Beat 或线程调度器执行 `check_scheduled_batches`
- 查询条件：`status == 'PENDING' AND scheduled_time <= func.now()`，按最早的 `scheduled_time` 执行
- 命中后调用 `SalaryCalculationService.execute_calculation_batch`
- 执行路径复用“立即计算”的逐条工作记录处理逻辑，避免规则上下文不一致

## 启动与运行

- 启动 FastAPI（示例）：
```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

- 启动 Celery Worker（监听队列 salary_calculation）：
```bash
celery -A src.app.core.celery_config.celery_app worker -Q salary_calculation -l info
```

- 启动 Celery Beat（定时触发）：
```bash
celery -A src.app.core.celery_config.celery_app beat -l info
```

- Windows 可直接使用仓库中的 `start_services.bat`（如有提供）启动相关服务。

## 手动触发与监控

- 手动触发检查任务：`POST /task-management/check-scheduled`
  - 返回 Celery 任务 ID，可用来查询状态
- 查询任务状态：`GET /task-management/status/{task_id}`
- 查看调度器线程状态：`GET /scheduler/status`

## 时间与时区（重要）

- 数据库与服务端统一使用 UTC；比较使用数据库时间 `func.now()`
- 前端传参建议：
  - 若按北京时间触发：使用 `+08:00` 偏移，例如 `2025-08-21T16:10:00+08:00`
  - 若已换算为 UTC：使用 `Z` 结尾，例如 `2025-08-21T08:10:00Z`
  - 若只能传“无时区”的时间（不推荐），后端按 `Asia/Shanghai` 解释并转为 UTC

## 常见问题与排查

- 定时没触发
  - 检查 Celery worker/beat 是否在运行
  - 确认批次 `status='PENDING'` 且 `scheduled_time` 已到（UTC 对比）
  - 查看应用日志中“Scheduler tick (UTC)”是否按分钟输出

- 规则执行报 `name 'hours' is not defined`
  - 已修复：定时批次执行逻辑复用逐条工作记录的上下文，包含 `worklog.hours`
  - 若仍有自定义规则，请确认规则变量映射正确（例如公式里的 `hours` 对应 `worklog.hours`）

- 结果金额为 0
  - 确认生效规则是否命中，或规则金额是否正确
  - 确认本次处理范围内存在 `status=0` 的工作记录（计算成功后会置为 1）

## 变更记录（摘要）

- 定时执行改用 `process_pending_worklogs` 路径，解决上下文变量缺失问题
- 统一时间标准为 UTC，`scheduled_time` 入库前标准化
- 每次分钟触发仅输出一次服务器 UTC 时间，减少日志噪声
