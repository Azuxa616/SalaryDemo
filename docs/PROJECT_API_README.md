# 项目管理API接口文档

## 概述

本项目提供了完整的项目管理API接口，支持项目的增删改查操作，并实现了基于角色的权限控制。

## 权限级别

- **1级（非正式员工）**: 只能查看项目
- **2级（正式员工）**: 只能查看项目  
- **3级（管理员）**: 可以查看、创建、更新、删除项目
- **4级（超级管理员）**: 可以查看、创建、更新、删除项目

## API接口

### 1. 获取项目列表

**接口**: `GET /projects/`

**权限要求**: 所有用户（1-4级）

**查询参数**:
- `skip`: 跳过的记录数（默认: 0）
- `limit`: 返回的记录数（默认: 100，最大: 1000）
- `name`: 项目名称搜索（可选）

**响应示例**:
```json
{
  "projects": [
    {
      "id": "uuid-string",
      "name": "薪资管理系统",
      "description": "员工薪资计算和管理系统",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 100
}
```



### 2. 创建项目

**接口**: `POST /projects/`

**权限要求**: 3级及以上（管理员、超级管理员）

**请求体**:
```json
{
  "name": "新项目名称",
  "description": "项目描述（可选）"
}
```

**响应**: 201 Created，返回创建的项目信息

### 3. 更新项目（完整更新）

**接口**: `PUT /projects/{project_id}`

**权限要求**: 3级及以上（管理员、超级管理员）

**路径参数**:
- `project_id`: 项目UUID

**请求体**:
```json
{
  "name": "更新后的项目名称",
  "description": "更新后的项目描述"
}
```

**响应**: 返回更新后的项目信息

### 4. 更新项目（部分更新）

**接口**: `PATCH /projects/{project_id}`

**权限要求**: 3级及以上（管理员、超级管理员）

**路径参数**:
- `project_id`: 项目UUID

**请求体**:
```json
{
  "name": "只更新名称"
}
```

**响应**: 返回更新后的项目信息

### 5. 删除项目

**接口**: `DELETE /projects/{project_id}`

**权限要求**: 3级及以上（管理员、超级管理员）

**路径参数**:
- `project_id`: 项目UUID

**响应**: 204 No Content

**注意事项**: 如果项目有关联的工作记录，则无法删除

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

### 错误响应示例

```json
{
  "detail": "项目名称已存在"
}
```

## 使用示例

### 1. 获取项目列表
```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/projects/?skip=0&limit=10"
```

### 2. 创建新项目
```bash
curl -X POST "http://localhost:8000/projects/" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"name": "新项目", "description": "项目描述"}'
```

### 3. 更新项目
```bash
curl -X PUT "http://localhost:8000/projects/<project-id>" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"name": "更新后的名称"}'
```

### 4. 删除项目
```bash
curl -X DELETE "http://localhost:8000/projects/<project-id>" \
     -H "Authorization: Bearer <token>"
```

## 数据库表结构

项目表 (`projects`) 包含以下字段：
- `id`: UUID主键
- `name`: 项目名称（VARCHAR(255)，唯一）
- `description`: 项目描述（TEXT，可选）
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 注意事项

1. 项目名称在系统中必须唯一（不区分大小写）
2. 删除项目前会检查是否有关联的工作记录
3. 所有时间字段使用UTC时区
4. 支持项目名称的模糊搜索
5. 分页查询支持自定义偏移量和限制数量
