# 员工薪资配置API文档

## 概述

员工薪资配置API提供了对员工薪资信息的完整管理功能，包括创建、查询、更新和删除操作。所有接口都实现了严格的权限控制，确保数据安全和访问控制。

## 权限等级说明

- **权限等级1**: 非正式员工
- **权限等级2**: 正式员工  
- **权限等级3**: 管理员
- **权限等级4**: 超级管理员

## API接口列表

### 1. 创建薪资配置

**接口**: `POST /salary-config/`

**权限要求**: 仅超级管理员(权限等级4)可使用

**功能**: 为指定员工创建新的薪资配置

**请求体**:
```json
{
    "employee_id": 123,
    "base_salary": "5000.00",
    "hourly_rate": "25.00",
    "overtime_rate": "1.5",
    "department_id": 1,
    "position": "软件工程师",
    "effective_from": "2024-01-01",
    "effective_to": null,
    "is_active": true
}
```

**响应示例**:
```json
{
    "id": "uuid-string",
    "employee_id": 123,
    "base_salary": "5000.00",
    "hourly_rate": "25.00",
    "overtime_rate": "1.5",
    "department_id": 1,
    "position": "软件工程师",
    "effective_from": "2024-01-01",
    "effective_to": null,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

**错误情况**:
- `400`: 该员工在指定生效日期已存在薪资配置
- `404`: 员工不存在
- `403`: 权限不足

---

### 2. 查询薪资配置列表

**接口**: `GET /salary-config/`

**权限要求**: 管理员及以上权限(等级3+)可使用

**功能**: 查询所有员工薪资配置，只能查看权限等级小于自身的员工

**查询参数**:
- `skip`: 跳过记录数 (默认: 0)
- `limit`: 返回记录数 (默认: 100, 最大: 1000)
- `employee_id`: 员工ID筛选 (可选)
- `department_id`: 部门ID筛选 (可选)
- `is_active`: 是否激活筛选 (可选)

**响应示例**:
```json
{
    "total": 10,
    "items": [
        {
            "id": "uuid-string",
            "employee_id": 123,
            "base_salary": "5000.00",
            "hourly_rate": "25.00",
            "overtime_rate": "1.5",
            "department_id": 1,
            "position": "软件工程师",
            "effective_from": "2024-01-01",
            "effective_to": null,
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ]
}
```

**权限控制**: 
- 超级管理员可查看所有配置
- 管理员只能查看权限等级小于自身的员工配置

---

### 3. 查询当前用户薪资配置

**接口**: `GET /salary-config/my`

**权限要求**: 所有用户都可使用

**功能**: 查询当前登录用户的薪资配置

**响应示例**:
```json
{
    "id": "uuid-string",
    "employee_id": 123,
    "base_salary": "5000.00",
    "hourly_rate": "25.00",
    "overtime_rate": "1.5",
    "department_id": 1,
    "position": "软件工程师",
    "effective_from": "2024-01-01",
    "effective_to": null,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

**错误情况**:
- `404`: 当前用户没有薪资配置

---

### 4. 根据ID查询薪资配置

**接口**: `GET /salary-config/{config_id}`

**权限要求**: 管理员及以上权限(等级3+)可使用

**功能**: 根据配置ID查询具体的薪资配置

**路径参数**:
- `config_id`: 薪资配置的UUID

**权限控制**: 只能查看权限等级小于自身的员工配置

**响应示例**: 同创建接口的响应

**错误情况**:
- `404`: 配置不存在
- `403`: 权限不足

---

### 5. 更新薪资配置

**接口**: `PUT /salary-config/{config_id}`

**权限要求**: 管理员及以上权限(等级3+)可使用

**功能**: 更新指定薪资配置的信息

**路径参数**:
- `config_id`: 薪资配置的UUID

**请求体** (所有字段都是可选的):
```json
{
    "base_salary": "6000.00",
    "hourly_rate": "30.00",
    "overtime_rate": "1.8",
    "department_id": 2,
    "position": "高级软件工程师",
    "effective_from": "2024-02-01",
    "effective_to": null,
    "is_active": true
}
```

**权限控制**: 只能修改权限等级小于自身的员工配置

**响应示例**: 返回更新后的完整配置信息

**错误情况**:
- `404`: 配置不存在
- `403`: 权限不足

---

### 6. 删除薪资配置

**接口**: `DELETE /salary-config/{config_id}`

**权限要求**: 仅超级管理员(权限等级4)可使用

**功能**: 软删除指定的薪资配置（设置为非激活状态）

**路径参数**:
- `config_id`: 薪资配置的UUID

**响应示例**:
```json
{
    "message": "Salary config deleted successfully"
}
```

**错误情况**:
- `404`: 配置不存在
- `403`: 权限不足

---

### 7. 查询指定员工的所有薪资配置

**接口**: `GET /salary-config/employee/{employee_id}`

**权限要求**: 管理员及以上权限(等级3+)可使用

**功能**: 查询指定员工的所有薪资配置记录

**路径参数**:
- `employee_id`: 员工ID

**权限控制**: 只能查看权限等级小于自身的员工配置

**响应示例**:
```json
[
    {
        "id": "uuid-string-1",
        "employee_id": 123,
        "base_salary": "5000.00",
        "hourly_rate": "25.00",
        "overtime_rate": "1.5",
        "department_id": 1,
        "position": "软件工程师",
        "effective_from": "2024-01-01",
        "effective_to": "2024-01-31",
        "is_active": false,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-31T00:00:00Z"
    },
    {
        "id": "uuid-string-2",
        "employee_id": 123,
        "base_salary": "6000.00",
        "hourly_rate": "30.00",
        "overtime_rate": "1.5",
        "department_id": 1,
        "position": "软件工程师",
        "effective_from": "2024-02-01",
        "effective_to": null,
        "is_active": true,
        "created_at": "2024-02-01T00:00:00Z",
        "updated_at": "2024-02-01T00:00:00Z"
    }
]
```

**排序**: 按生效日期降序排列

---

## 权限控制规则

### 1. 创建权限
- 只有超级管理员(权限等级4)可以创建薪资配置

### 2. 查询权限
- **查询所有配置**: 管理员及以上权限(等级3+)
- **查询自己的配置**: 所有用户
- **查询特定配置**: 管理员及以上权限(等级3+)
- **权限过滤**: 只能查看权限等级小于自身的员工配置

### 3. 修改权限
- 管理员及以上权限(等级3+)可以修改
- 只能修改权限等级小于自身的员工配置

### 4. 删除权限
- 只有超级管理员(权限等级4)可以删除

## 数据模型

### EmployeeSalaryConfigCreate
```python
class EmployeeSalaryConfigCreate(BaseModel):
    employee_id: int
    base_salary: Decimal = Decimal('0')
    hourly_rate: Decimal = Decimal('0')
    overtime_rate: Decimal = Decimal('1.5')
    department_id: Optional[int] = None
    position: Optional[str] = None
    effective_from: date = date.today()
    effective_to: Optional[date] = None
    is_active: bool = True
```

### EmployeeSalaryConfigUpdate
```python
class EmployeeSalaryConfigUpdate(BaseModel):
    base_salary: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    overtime_rate: Optional[Decimal] = None
    department_id: Optional[int] = None
    position: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None
```

### EmployeeSalaryConfigOut
```python
class EmployeeSalaryConfigOut(BaseModel):
    id: str
    employee_id: int
    base_salary: Decimal
    hourly_rate: Decimal
    overtime_rate: Decimal
    department_id: Optional[int]
    position: Optional[str]
    effective_from: date
    effective_to: Optional[date]
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

## 使用示例

### 1. 超级管理员创建薪资配置
```bash
curl -X POST "http://localhost:8000/salary-config/" \
  -H "Authorization: Bearer {superadmin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 123,
    "base_salary": "5000.00",
    "hourly_rate": "25.00",
    "overtime_rate": "1.5",
    "department_id": 1,
    "position": "软件工程师"
  }'
```

### 2. 管理员查询薪资配置列表
```bash
curl -X GET "http://localhost:8000/salary-config/?limit=10&skip=0" \
  -H "Authorization: Bearer {admin_token}"
```

### 3. 员工查询自己的薪资配置
```bash
curl -X GET "http://localhost:8000/salary-config/my" \
  -H "Authorization: Bearer {employee_token}"
```

### 4. 管理员更新薪资配置
```bash
curl -X PUT "http://localhost:8000/salary-config/{config_id}" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "base_salary": "6000.00",
    "hourly_rate": "30.00"
  }'
```

## 测试

可以使用提供的测试脚本 `test_salary_config_api.py` 来验证所有功能：

```bash
python test_salary_config_api.py
```

## 注意事项

1. **权限控制**: 所有接口都严格遵循权限等级控制
2. **数据完整性**: 创建时会检查员工是否存在和配置是否重复
3. **软删除**: 删除操作采用软删除方式，只设置is_active为false
4. **事务安全**: 所有数据库操作都在事务中执行
5. **类型安全**: 使用Pydantic模型确保数据类型正确性
6. **错误处理**: 提供详细的错误信息和HTTP状态码
