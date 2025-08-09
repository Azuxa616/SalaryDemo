## SalaryDemo

一个基于 FastAPI + SQLAlchemy + PostgreSQL 的示例项目，内置用户注册/登录与基于角色的鉴权，提供可视化的 Swagger 文档，并在启动时在控制台打印 Base URL 与文档地址。

### 技术栈
- **后端框架**: [FastAPI](https://fastapi.tiangolo.com/)
- **Web 服务器**: [uvicorn](https://www.uvicorn.org/)
- **数据访问**: SQLAlchemy
- **数据库**: PostgreSQL（`psycopg` 驱动）
- **认证**: JWT（`python-jose`）、密码哈希（`passlib[bcrypt]`）


## 快速开始（Windows / PowerShell）

### 1) 创建并激活虚拟环境
```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
```

### 2) 安装依赖
项目已固定 `passlib[bcrypt]==1.7.4` 与 `bcrypt==4.0.1` 以避免兼容性问题。
```powershell
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt
```

### 3) 配置数据库连接
默认连接串见 `src/app/core/config.py`：
```
postgresql+psycopg://postgres:postgres@localhost:5432/SalaryDemoDB
```
若你的 PostgreSQL 超管密码为 `root`，请在运行前设置：
```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:root@localhost:5432/SalaryDemoDB"
```
也可在 IDE 启动配置的 Environment variables 中设置。

### 4) 初始化数据库
首次运行前创建数据库并执行初始化脚本（启用 `pgcrypto`，创建 `users` 表，并预置 `admin/root` 超管账号）：
```powershell
$env:PGPASSWORD = "<你的postgres密码>"
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE \"SalaryDemoDB\";"
psql -U postgres -h localhost -d SalaryDemoDB -f "sql\init_auth.sql"
```

### 5) 启动服务
推荐以模块方式运行 uvicorn，并设置应用目录以保证导入路径正确：
```powershell
uvicorn --app-dir src main:app --reload --host 127.0.0.1 --port 8000
```
启动后控制台会打印：
```
======================================================================
 FastAPI 服务已启动
 Base URL : http://127.0.0.1:8000
 Swagger  : http://127.0.0.1:8000/docs
 ReDoc    : http://127.0.0.1:8000/redoc
======================================================================
```

也可以通过环境变量覆盖显示地址（需与 uvicorn 启动参数保持一致）：
```powershell
$env:APP_HOST = "127.0.0.1"
$env:APP_PORT = "8000"
# 或者直接指定 BASE_URL（会覆盖 APP_HOST/APP_PORT）
$env:BASE_URL = "http://127.0.0.1:8000"
```

## 使用 PyCharm 启动（推荐配置）
- 新建 Run/Debug Configuration → 选择 "Python"
- Module name: `uvicorn`
- Parameters: `--app-dir src main:app --reload --host 127.0.0.1 --port 8000`
- Working directory: 项目根目录（例如 `F:\\Work\\projects\\SalaryDemo`）
- Python interpreter: 选择 `.venv\Scripts\python.exe`
- Environment variables: 设置 `DATABASE_URL=postgresql+psycopg://postgres:<你的密码>@localhost:5432/SalaryDemoDB`
- 勾选 “Add content roots to PYTHONPATH” 和 “Add source roots to PYTHONPATH”

若你的 PyCharm 是 Professional 版本，也可使用内置 FastAPI 配置：
- Host: `127.0.0.1`
- Port: `8000`
- Module name: `src.main`
- Application instance: `app`
- Additional options: `--reload`

## 环境变量
- **DATABASE_URL**: 数据库连接串，示例：`postgresql+psycopg://postgres:root@localhost:5432/SalaryDemoDB`
- **SECRET_KEY**: JWT 密钥（默认 `dev-secret-change-me`，生产务必修改）
- **ACCESS_TOKEN_EXPIRE_MINUTES**: 访问令牌过期时间，默认 `60`
- **APP_HOST / APP_PORT**: 启动横幅显示用主机与端口，默认 `127.0.0.1` / `8000`
- **BASE_URL**: 覆盖横幅显示的完整基础地址（设置后优先生效）

## API 速览
文档页面：`http://127.0.0.1:8000/docs`

### 注册（POST `/auth/register`）
请求体（JSON）：
```json
{
  "username": "alice",
  "password": "secret123",
  "email": "alice@example.com",
  "full_name": "Alice",
  "role": 2
}
```

### 登录（POST `/auth/login`，JSON）
```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"root"}'
```

### 颁发令牌（POST `/auth/token`，表单）
```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/auth/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=root"
```

### 获取当前用户（GET `/auth/me`，需要 Bearer Token）
请求头：`Authorization: Bearer <access_token>`

## 常见问题排查（FAQ）
- **PostgreSQL 认证失败（password authentication failed）**
  - 运行时 `DATABASE_URL` 的用户名/密码必须与数据库实际一致（常见错误是密码仍为 `postgres`）
  - 确认数据库存在：`psql -U postgres -h localhost -l`
  - 如未初始化，执行 `sql/init_auth.sql` 以创建表和预置账号

- **导入错误 `ModuleNotFoundError: No module named 'app'`**
  - 使用 `uvicorn --app-dir src main:app ...`，或将 `PYTHONPATH` 指向 `src`，或把工作目录改为 `src`

- **登录时报 `(trapped) error reading bcrypt version`**
  - 已固定依赖版本：`passlib[bcrypt]==1.7.4`、`bcrypt==4.0.1`
  - 如仍报错：`pip uninstall -y bcrypt passlib` 后重新 `pip install -r requirements.txt`

- **HTTP 422（Unprocessable Content）**
  - `/auth/login` 需要 JSON 请求体
  - `/auth/token` 需要 `application/x-www-form-urlencoded` 表单

- **端口占用**
  - 修改端口：`--port 8001`

## 生产部署（简述）
- 使用 `--host 0.0.0.0` 并结合进程管理器（如 `gunicorn` + `uvicorn.workers.UvicornWorker` 或 Windows 下的服务管理方式）
- 使用强随机的 `SECRET_KEY`，并通过安全的方式管理环境变量
- 启用持久化日志与监控；数据库启用备份与访问控制

## 预置账号说明
- 执行 `sql/init_auth.sql` 后，默认会创建：
  - 用户名：`admin`
  - 密码：`root`
- 请在首次登录后尽快修改密码


