# 注册API薪资配置功能说明

## 功能概述

在用户注册成功后，系统会自动在员工薪资配置表（`employee_salary_configs`）中为该用户创建默认的薪资配置。

## 实现细节

### 1. 修改的文件

- `src/app/api/routes/auth.py` - 注册API的主要实现

### 2. 新增功能

在 `register` 函数中，用户注册成功后会自动创建薪资配置：

```python
# 为新注册用户添加默认薪资配置
salary_config = EmployeeSalaryConfig(
    employee_id=user.id,
    base_salary=0,  # 默认基本工资为0
    hourly_rate=0,  # 默认时薪为0
    overtime_rate=1.5,  # 默认加班倍率为1.5
    is_active=True
)
db.add(salary_config)
db.commit()
```

### 3. 默认值设置

- **基本工资 (base_salary)**: 0 - 需要后续手动设置
- **时薪 (hourly_rate)**: 0 - 需要后续手动设置  
- **加班倍率 (overtime_rate)**: 1.5 - 使用系统默认值
- **生效日期 (effective_from)**: 当前日期（自动设置）
- **状态 (is_active)**: True - 配置生效

### 4. 错误处理

- 使用 try-catch 包装整个注册过程
- 如果任何步骤失败，会回滚数据库事务
- 返回详细的错误信息

## 数据库表结构

### employee_salary_configs 表

```sql
CREATE TABLE employee_salary_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id BIGINT NOT NULL REFERENCES users(id),
    base_salary DECIMAL(10,2) NOT NULL DEFAULT 0,
    hourly_rate DECIMAL(8,2) NOT NULL DEFAULT 0,
    overtime_rate DECIMAL(5,2) NOT NULL DEFAULT 1.5,
    department_id INTEGER,
    position VARCHAR(100),
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 使用流程

1. 用户调用 `/auth/register` API 进行注册
2. 系统验证用户名唯一性
3. 创建用户账户
4. 自动创建默认薪资配置
5. 返回用户信息

## 注意事项

1. **薪资配置需要后续完善**: 默认的基本工资和时薪都设置为0，需要管理员或HR后续手动设置
2. **事务一致性**: 如果薪资配置创建失败，整个注册过程会回滚
3. **唯一性约束**: 每个员工在每个生效日期只能有一个薪资配置
4. **权限控制**: 薪资配置的修改需要相应的权限

## 测试

可以使用提供的测试脚本 `test_register.py` 来验证功能：

```bash
python test_register.py
```

## 后续改进建议

1. 添加薪资配置查询API
2. 实现薪资配置的批量导入功能
3. 添加薪资配置的版本控制
4. 实现薪资配置的审批流程
5. 添加薪资配置的变更日志
