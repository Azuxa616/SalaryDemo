# 薪资计算API使用说明

## 概述

新增的薪资计算接口支持两种计算模式：
1. **立即计算**：立即触发薪资计算
2. **定时计算**：在指定时间执行薪资计算

## API接口

### 1. 计算薪资接口

**接口地址：** `POST /salary-calculation/calculate-salary`

**权限要求：** 管理员及以上权限（role >= 3）

#### 请求参数

```json
{
  "calculation_type": "IMMEDIATE",  // 或 "SCHEDULED"
  "scheduled_time": null,           // 定时计算时间，立即计算时为null
  "batch_name": null,               // 批次名称，定时计算时必填
  "period_start": "2024-01-01",    // 计算开始日期（可选）
  "period_end": "2024-01-31",      // 计算结束日期（可选）
  "calculation_period": "CUSTOM",   // 计算周期：MONTHLY/WEEKLY/CUSTOM
  "description": "月度薪资计算"      // 计算描述（可选）
}
```

#### 使用示例

**立即计算：**
```bash
curl -X POST "http://localhost:8000/salary-calculation/calculate-salary" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "calculation_type": "IMMEDIATE",
    "period_start": "2024-01-01",
    "period_end": "2024-01-31",
    "description": "1月份薪资计算"
  }'
```

**定时计算：**
```bash
curl -X POST "http://localhost:8000/salary-calculation/calculate-salary" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "calculation_type": "SCHEDULED",
    "scheduled_time": "2024-02-01T09:00:00Z",  
    "batch_name": "2月份薪资计算",
    "period_start": "2024-02-01",
    "period_end": "2024-02-29",
    "calculation_period": "MONTHLY",
    "description": "2月份月度薪资计算"
  }'
```

### 时间格式与时区（重要）

- 服务器与数据库统一使用 UTC，后端会将前端传入的 `scheduled_time` 标准化为 UTC 入库。
- 推荐总是传“带时区”的 ISO8601 时间：
  - 北京时间 2025-08-21 16:10 触发：`"2025-08-21T16:10:00+08:00"`
  - 等价的 UTC：`"2025-08-21T08:10:00Z"`
- 如果只能传“无时区”的时间（不推荐），后端按 `Asia/Shanghai` 解释并转换为 UTC。
- 提交样例（本地 +08:00）：
```bash
curl -X POST "http://localhost:8000/salary-calculation/calculate-salary" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "calculation_type": "SCHEDULED",
    "scheduled_time": "2025-08-21T16:10:00+08:00",
    "batch_name": "2月份薪资计算",
    "period_start": "2024-02-01",
    "period_end": "2024-02-29",
    "calculation_period": "MONTHLY",
    "description": "2月份月度薪资计算"
  }'
```

#### 响应格式

**立即计算响应：**
```json
{
  "success": true,
  "message": "处理完成，成功: 5, 失败: 0",
  "calculation_id": null,
  "batch_id": null,
  "scheduled_time": null,
  "data": {
    "processed_count": 5,
    "success_count": 5,
    "error_count": 0,
    "processed_worklogs": [...]
  }
}
```

**定时计算响应：**
```json
{
  "success": true,
  "message": "定时计算批次创建成功，ID: uuid-123",
  "calculation_id": null,
  "batch_id": "uuid-123",
  "scheduled_time": "2024-02-01T09:00:00Z",
  "data": null
}
```

### 2. 获取计算批次列表

**接口地址：** `GET /salary-calculation/calculation-batches`

**权限要求：** 管理员及以上权限（role >= 3）

#### 查询参数

- `status`: 批次状态筛选（可选）
- `skip`: 跳过记录数（默认0）
- `limit`: 返回记录数（默认100，最大1000）

#### 使用示例

```bash
# 获取所有批次
curl "http://localhost:8000/salary-calculation/calculation-batches" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取待执行的批次
curl "http://localhost:8000/salary-calculation/calculation-batches?status=SCHEDULED" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 分页查询
curl "http://localhost:8000/salary-calculation/calculation-batches?skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 响应格式

```json
[
  {
    "id": "uuid-123",
    "batch_name": "2月份薪资计算",
    "calculation_period": "MONTHLY",
    "period_start": "2024-02-01",
    "period_end": "2024-02-29",
    "status": "SCHEDULED",
    "scheduled_time": "2024-02-01T09:00:00Z",
    "total_employees": 0,
    "processed_count": 0,
    "success_count": 0,
    "error_count": 0,
    "total_amount": 0.0,
    "created_at": "2024-01-15T10:00:00Z",
    "started_at": null,
    "completed_at": null,
    "description": "2月份月度薪资计算"
  }
]
```

### 3. 执行定时计算批次

**接口地址：** `POST /salary-calculation/execute-scheduled-batch/{batch_id}`

**权限要求：** 管理员及以上权限（role >= 3）

#### 使用示例

```bash
curl -X POST "http://localhost:8000/salary-calculation/execute-scheduled-batch/uuid-123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 响应格式

```json
{
  "success": true,
  "message": "批次 uuid-123 执行成功",
  "batch_id": "uuid-123"
}
```

### 4. 删除计算批次

**接口地址：** `DELETE /salary-calculation/calculation-batch/{batch_id}`

**权限要求：** 超级管理员权限（role >= 4）

#### 使用示例

```bash
curl -X DELETE "http://localhost:8000/salary-calculation/calculation-batch/uuid-123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 响应格式

```json
{
  "success": true,
  "message": "批次 uuid-123 删除成功"
}
```

## 状态说明

### 计算批次状态

- `PENDING`: 待处理（默认状态）
- `SCHEDULED`: 已定时（等待执行）
- `PROCESSING`: 处理中
- `COMPLETED`: 已完成
- `FAILED`: 执行失败
- `CANCELLED`: 已取消

### 计算周期

- `MONTHLY`: 月度计算
- `WEEKLY`: 周度计算
- `CUSTOM`: 自定义周期

## 使用场景

### 1. 立即计算场景

- 临时需要计算特定时间段的薪资
- 测试薪资计算功能
- 紧急薪资计算需求

### 2. 定时计算场景

- 每月固定时间计算薪资
- 每周定期计算工时
- 节假日后的批量计算

## 注意事项

1. **权限控制**：只有管理员及以上权限可以使用这些接口
2. **定时执行**：定时计算需要配合定时任务系统使用
3. **批次管理**：定时批次创建后需要手动执行或通过定时任务执行
4. **数据一致性**：计算过程中使用事务确保数据一致性
5. **错误处理**：计算失败时会记录详细错误日志

## 定时任务集成

要实现真正的定时执行，需要配合定时任务系统（如Celery、APScheduler等）：

```python
# 示例：使用APScheduler定时执行
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

# 每天凌晨2点执行待处理的定时批次
scheduler.add_job(
    execute_scheduled_batches,
    CronTrigger(hour=2, minute=0),
    id='daily_salary_calculation'
)

scheduler.start()
```

## 错误处理

常见错误及解决方案：

1. **权限不足**：检查用户角色是否满足要求
2. **参数错误**：确保必填字段已填写
3. **时间格式错误**：使用ISO 8601格式的时间字符串
4. **批次不存在**：检查批次ID是否正确
5. **状态错误**：确保批次状态允许执行相应操作
