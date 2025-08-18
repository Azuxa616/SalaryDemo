# 薪资计算引擎功能说明

## 概述

薪资计算引擎已经实现了您要求的四个核心功能，可以自动处理待核算的工作记录并计算薪资。

## 功能清单

### ✅ 功能1：检查未核算的工作记录
- 自动筛选数据库中 `status = 0`（未核算）的工作记录
- 支持按日期范围筛选
- 返回待处理记录列表

### ✅ 功能2：检查员工薪资设置
- 根据员工ID和日期查找有效的薪资配置
- 检查基本工资、时薪、加班倍率等设置
- 验证配置的有效期和激活状态

### ✅ 功能3：使用薪资规则计算薪资
- 应用已启用的薪资规则（RATE、FIXED、CONDITIONAL）
- 按优先级顺序执行规则
- 支持变量引用和条件判断
- 计算总金额和净金额

### ✅ 功能4：更新状态和保存结果
- 计算成功后自动将工作记录状态更新为 `1`（已核算）
- 将计算结果保存到 `salary_calculation_results` 表
- 支持增量更新和新建记录

## 使用方法

### 1. API调用

```bash
# 处理所有待核算的工作记录
POST /api/salary-config/process-pending-worklogs

# 处理指定日期范围的待核算记录
POST /api/salary-config/process-pending-worklogs?period_start=2024-01-01&period_end=2024-01-31
```

**权限要求：** 只有管理员及以上权限（role >= 3）可以执行此操作

### 2. 服务调用

```python
from app.services.salary_calculation_service import SalaryCalculationService

# 创建服务实例
service = SalaryCalculationService(db)

# 处理所有待核算记录
result = service.process_pending_worklogs()

# 处理指定日期范围
result = service.process_pending_worklogs(
    period_start=date(2024, 1, 1),
    period_end=date(2024, 1, 31)
)
```

### 3. 返回结果格式

```json
{
  "success": true,
  "message": "处理完成，成功: 5, 失败: 0",
  "data": {
    "processed_count": 5,
    "success_count": 5,
    "error_count": 0,
    "processed_worklogs": [
      {
        "worklog_id": "uuid-123",
        "employee_id": 1,
        "date": "2024-01-15",
        "calculated_amount": 150.00
      }
    ]
  }
}
```

## 核心方法说明

### `process_pending_worklogs()`
主要处理方法，整合了所有四个功能：
1. 获取待核算记录
2. 检查薪资配置
3. 执行薪资计算
4. 更新状态和保存结果

### `_get_pending_worklogs()`
获取所有 `status = 0` 的工作记录，支持日期范围筛选。

### `_calculate_single_worklog_salary()`
计算单条工作记录的薪资，包括：
- 构建计算上下文
- 应用薪资规则
- 计算扣除项
- 返回计算结果

### `_save_worklog_calculation_result()`
保存计算结果到数据库，支持：
- 新建记录
- 更新现有记录
- 增量计算

## 薪资规则支持

### 规则类型
- **RATE**: 比率计算（如：工时 × 时薪 × 倍率）
- **FIXED**: 固定金额（如：交通补助500元）
- **CONDITIONAL**: 条件规则（如：深夜工作津贴）

### 变量引用
支持在公式中引用上下文变量：
- `employee.base_salary`: 员工基本工资
- `worklog.hours`: 工作工时
- `employee.hourly_rate`: 员工时薪

### 示例规则
```sql
-- 基本工资
INSERT INTO salary_rules (name, rule_type, formula) 
VALUES ('基本工资', 'FIXED', 'base_salary');

-- 加班费
INSERT INTO salary_rules (name, rule_type, formula) 
VALUES ('加班费', 'RATE', 'overtime_hours * hourly_rate * overtime_multiplier');

-- 深夜津贴
INSERT INTO salary_rules (name, rule_type, formula, conditions) 
VALUES ('深夜津贴', 'CONDITIONAL', 'hours * 30', '{"work_time": "> 22:00"}');
```

## 数据库表结构

### 主要表
- `worklogs`: 工作记录表
- `salary_rules`: 薪资规则表
- `employee_salary_configs`: 员工薪资配置表
- `salary_calculation_results`: 薪资计算结果表
- `deduction_configs`: 扣除项配置表

### 状态说明
- `worklogs.status`: 0=待核算，1=已核算，2=保留
- `salary_calculation_results.status`: CALCULATED=已计算，APPROVED=已批准，PAID=已发放

## 错误处理

### 常见错误
1. **员工无薪资配置**: 跳过该记录，记录错误日志
2. **规则执行失败**: 记录错误信息，继续处理其他规则
3. **数据库操作失败**: 回滚事务，返回错误信息

### 日志记录
所有操作都会记录详细的日志信息，包括：
- 处理进度
- 成功/失败统计
- 错误详情
- 计算结果

## 性能优化

### 批量处理
- 支持批量处理多条工作记录
- 事务管理确保数据一致性
- 错误隔离，单条记录失败不影响其他记录

### 索引优化
- 工作记录表：`status`, `employee_id`, `date`
- 薪资配置表：`employee_id`, `effective_from`, `is_active`
- 薪资规则表：`rule_type`, `is_active`, `priority`

## 测试和验证

### 运行测试
```bash
python test_salary_engine.py
```

### 验证要点
1. 检查待核算记录数量
2. 验证薪资配置完整性
3. 确认规则执行结果
4. 检查状态更新和结果保存

## 注意事项

1. **权限控制**: 只有管理员可以执行批量处理操作
2. **数据一致性**: 使用事务确保操作的原子性
3. **错误恢复**: 支持部分失败的情况，可以重新处理失败的记录
4. **性能考虑**: 大量记录处理时建议分批进行

## 扩展功能

### 未来改进
- 支持更复杂的条件表达式
- 添加薪资计算模板
- 支持多币种计算
- 集成审批流程
- 添加计算历史追踪
