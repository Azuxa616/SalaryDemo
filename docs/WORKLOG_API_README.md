# 工作记录管理API接口文档

## 概述

本项目提供了完整的工作记录管理API接口，支持工作记录的增删改查操作，并实现了基于角色的权限控制。

## 权限级别

- **1级（非正式员工）**: 只能新增、查看、修改和删除自己的"未核算"状态记录
- **2级（正式员工）**: 只能新增、查看、修改和删除自己的"未核算"状态记录  
- **3级（管理员）**: 可以查看、创建、更新、删除所有记录，可以修改记录状态
- **4级（超级管理员）**: 可以查看、创建、更新、删除所有记录，可以修改记录状态

## 状态说明

- **0**: 待核算 - 新创建的工作记录默认状态
- **1**: 已核算 - 经过薪资计算引擎处理后的状态
- **2**: 保留状态 - 为将来扩展预留的状态

## API接口

### 1. 获取工作记录列表

**接口**: `GET /worklogs/`

**权限要求**: 所有用户（1-4级）

**查询参数**:
- `skip`: 跳过的记录数（默认: 0）
- `limit`: 返回的记录数（默认: 100，最大: 1000）
- `employee_id`: 员工ID筛选（可选）
- `project_id`: 项目ID筛选（可选）
- `date_from`: 开始日期筛选（可选）
- `date_to`: 结束日期筛选（可选）
- `status`: 状态筛选（可选，0=待核算，1=已核算，2=保留）

**权限限制**:
- 2级及以下用户只能查看自己的记录
- 3-4级用户可以查看所有记录

**响应示例**:
```json
{
  "worklogs": [
    {
      "entry_id": "uuid-string",
      "employee_id": 1,
      "date": "2024-01-01",
      "project_id": "project-uuid",
      "task_type": "开发",
      "hours": 8.0,
      "remarks": "完成用户管理模块",
      "ext_field": "高优先级",
      "status": 0,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 100
}
```

### 2. 获取工作记录详情

**接口**: `GET /worklogs/{worklog_id}`

**权限要求**: 所有用户（1-4级）

**路径参数**:
- `worklog_id`: 工作记录UUID

**权限限制**:
- 2级及以下用户只能查看自己的记录
- 3-4级用户可以查看所有记录

**响应示例**:
```json
{
  "entry_id": "uuid-string",
  "employee_id": 1,
  "date": "2024-01-01",
  "project_id": "project-uuid",
  "task_type": "开发",
  "hours": 8.0,
  "remarks": "完成用户管理模块",
  "ext_field": "高优先级",
  "status": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 3. 创建工作记录

**接口**: `POST /worklogs/`

**权限要求**: 所有用户（1-4级）

**权限限制**:
- 2级及以下用户只能为自己创建记录
- 3-4级用户可以为任何员工创建记录

**请求体**:
```json
{
  "employee_id": 1,
  "date": "2024-01-01",
  "project_id": "project-uuid",
  "task_type": "开发",
  "hours": 8.0,
  "remarks": "完成用户管理模块",
  "ext_field": "高优先级"
}
```

**响应**: 201 Created，返回创建的工作记录信息

**注意事项**:
- 新创建的工作记录状态默认为0（待核算）
- 系统会自动验证员工ID和项目ID是否存在

### 4. 更新工作记录（完整更新）

**接口**: `PUT /worklogs/{worklog_id}`

**权限要求**: 所有用户（1-4级）

**路径参数**:
- `worklog_id`: 工作记录UUID

**权限限制**:
- 2级及以下用户只能修改状态为"未核算"(0)的记录
- 3-4级用户可以修改任何状态的记录

**请求体**:
```json
{
  "employee_id": 1,
  "date": "2024-01-01",
  "project_id": "project-uuid",
  "task_type": "测试",
  "hours": 6.0,
  "remarks": "单元测试",
  "ext_field": "中优先级"
}
```

**响应**: 返回更新后的工作记录信息

### 5. 更新工作记录（部分更新）

**接口**: `PATCH /worklogs/{worklog_id}`

**权限要求**: 所有用户（1-4级）

**路径参数**:
- `worklog_id`: 工作记录UUID

**权限限制**:
- 2级及以下用户只能修改状态为"未核算"(0)的记录
- 3-4级用户可以修改任何状态的记录

**请求体**:
```json
{
  "hours": 7.0,
  "remarks": "更新后的备注"
}
```

**响应**: 返回更新后的工作记录信息

### 6. 删除工作记录

**接口**: `DELETE /worklogs/{worklog_id}`

**权限要求**: 所有用户（1-4级）

**路径参数**:
- `worklog_id`: 工作记录UUID

**权限限制**:
- 2级及以下用户只能删除状态为"未核算"(0)的记录
- 3-4级用户可以删除任何状态的记录

**响应**: 204 No Content

### 7. 更新工作记录状态

**接口**: `PATCH /worklogs/{worklog_id}/status`

**权限要求**: 3级及以上（管理员、超级管理员）

**路径参数**:
- `worklog_id`: 工作记录UUID

**查询参数**:
- `new_status`: 新状态值（0=待核算，1=已核算，2=保留）

**响应示例**:
```json
{
  "message": "状态更新成功",
  "worklog_id": "uuid-string",
  "new_status": 1
}
```

### 8. 获取工作记录统计

**接口**: `GET /worklogs/summary/statistics`

**权限要求**: 所有用户（1-4级）

**查询参数**:
- `employee_id`: 员工ID筛选（可选）
- `project_id`: 项目ID筛选（可选）
- `date_from`: 开始日期筛选（可选）
- `date_to`: 结束日期筛选（可选）

**权限限制**:
- 2级及以下用户只能查看自己的统计
- 3-4级用户可以查看所有统计

**响应示例**:
```json
{
  "total_records": 10,
  "total_hours": 80.5,
  "status_breakdown": [
    {
      "status": 0,
      "count": 5,
      "total_hours": 40.0
    },
    {
      "status": 1,
      "count": 3,
      "total_hours": 24.0
    },
    {
      "status": 2,
      "count": 2,
      "total_hours": 16.5
    }
  ]
}
```

## 认证方式

所有API接口都需要通过JWT Token进行认证，在请求头中添加：

```
Authorization: Bearer <your-jwt-token>
```

## 错误处理

### 常见HTTP状态码

- **200 OK**: 请求成功
- **201 Created**: 资源创建成功
- **204 No Content**: 删除成功
- **400 Bad Request**: 请求参数错误
- **401 Unauthorized**: 未认证或Token无效
- **403 Forbidden**: 权限不足
- **404 Not Found**: 资源不存在
- **422 Unprocessable Entity**: 请求体验证失败
- **500 Internal Server Error**: 服务器内部错误

### 错误响应示例

**权限不足**:
```json
{
  "detail": "权限不足：只能查看自己的工作记录"
}
```

**记录不存在**:
```json
{
  "detail": "工作记录不存在"
}
```

**状态限制**:
```json
{
  "detail": "权限不足：只能修改未核算的工作记录"
}
```

## 使用示例

### 1. 获取工作记录列表
```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/worklogs/?skip=0&limit=10&status=0"
```

### 2. 创建新工作记录
```bash
curl -X POST "http://localhost:8000/worklogs/" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "employee_id": 1,
       "date": "2024-01-01",
       "project_id": "project-uuid",
       "task_type": "开发",
       "hours": 8.0,
       "remarks": "完成用户管理模块"
     }'
```

### 3. 更新工作记录
```bash
curl -X PUT "http://localhost:8000/worklogs/<worklog-id>" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"hours": 7.0, "remarks": "更新后的备注"}'
```

### 4. 更新记录状态
```bash
curl -X PATCH "http://localhost:8000/worklogs/<worklog-id>/status?new_status=1" \
     -H "Authorization: Bearer <token>"
```

### 5. 删除工作记录
```bash
curl -X DELETE "http://localhost:8000/worklogs/<worklog-id>" \
     -H "Authorization: Bearer <token>"
```

## 数据库表结构

工作记录表 (`worklogs`) 包含以下字段：
- `entry_id`: UUID主键
- `employee_id`: 员工ID（外键关联users表）
- `date`: 工作日期
- `project_id`: 项目ID（外键关联projects表）
- `task_type`: 任务类型
- `hours`: 工时
- `remarks`: 备注信息
- `status`: 核算状态（0=待核算，1=已核算，2=保留）
- `ext_field`: 扩展字段
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 注意事项

1. 工作记录状态管理严格，只有管理员可以修改状态
2. 2级及以下用户的操作受到严格限制，确保数据安全
3. 支持多种筛选条件，便于数据查询和分析
4. 扩展字段为将来功能扩展预留
5. 所有时间字段使用UTC时区
6. 外键约束确保数据完整性
