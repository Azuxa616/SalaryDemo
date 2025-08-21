# Celery 定时任务系统部署指南

## 概述

本系统使用 Celery + Redis 实现薪资计算的定时任务调度，采用简化的设计理念：**每分钟检查一次，每次只处理一个最早到达核算时间的批次**。

## 系统架构

```
FastAPI 应用 → Celery Beat (调度器) → Redis → Celery Worker (执行器) → 数据库
```

## 核心特性

- **智能调度**: 每分钟自动检查待执行批次
- **优先级处理**: 优先处理最早到达核算时间的批次
- **资源控制**: 每分钟最多处理一个批次，确保系统稳定性
- **自动恢复**: 支持失败批次的重试机制

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动 Redis 服务

### Windows
```bash
# 下载 Redis for Windows
# 启动 Redis 服务
redis-server
```

### Linux/macOS
```bash
# 安装 Redis
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis                 # macOS

# 启动服务
sudo systemctl start redis        # Ubuntu/Debian
brew services start redis         # macOS
```

## 启动定时任务系统

### 方式1: 使用启动脚本（推荐）
```bash
python start_celery.py
```

### 方式2: 手动启动
```bash
# 终端1: 启动 Worker（并发数设为1，确保每分钟只处理一个批次）
celery -A src.app.core.celery_config.celery_app worker --loglevel=info --concurrency=1

# 终端2: 启动 Beat (调度器)
celery -A src.app.core.celery_config.celery_app beat --loglevel=info
```

## 定时任务配置

### 核心任务

| 任务名称 | 执行频率 | 说明 |
|---------|---------|------|
| `check_scheduled_batches` | 每分钟 | 检查待执行的定时批次，每次只处理一个最早到达核算时间的批次 |

### 任务参数配置

在 `src/app/core/celery_config.py` 中可以调整：
- 执行频率：当前为每分钟
- 并发数：设置为1，确保每分钟只处理一个批次
- 超时时间：5分钟
- 重试策略：支持失败重试

## API 接口

### 手动触发任务

```bash
# 手动触发检查定时批次（用于测试）
POST /salary-calculation/tasks/check-scheduled
```

### 查询任务状态

```bash
# 查询任务执行状态
GET /salary-calculation/tasks/status/{task_id}

# 查询活跃任务
GET /salary-calculation/tasks/active
```

## 监控和管理

### 查看任务状态
```bash
# 查看 Worker 状态
celery -A src.app.core.celery_config.celery_app inspect active

# 查看队列状态
celery -A src.app.core.celery_config.celery_app inspect stats
```

### 停止任务
```bash
# 停止所有 Worker
celery -A src.app.core.celery_config.celery_app control shutdown

# 停止 Beat
# 直接终止 beat 进程
```

## 故障排除

### 常见问题

1. **Redis 连接失败**
   - 检查 Redis 服务是否启动
   - 确认端口 6379 是否开放
   - 检查防火墙设置

2. **任务执行失败**
   - 查看 Worker 日志
   - 检查数据库连接
   - 验证任务参数

3. **定时任务不执行**
   - 确认 Beat 进程是否运行
   - 检查任务配置是否正确
   - 查看 Beat 日志

### 日志查看

```bash
# Worker 日志
celery -A src.app.core.celery_config.celery_app worker --loglevel=debug

# Beat 日志
celery -A src.app.core.celery_config.celery_app beat --loglevel=debug
```

## 生产环境部署

### 使用 Supervisor 管理进程

```ini
[program:celery_worker]
command=celery -A src.app.core.celery_config.celery_app worker --loglevel=info --concurrency=1
directory=/path/to/your/project
user=celery
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:celery_beat]
command=celery -A src.app.core.celery_config.celery_app beat --loglevel=info
directory=/path/to/your/project
user=celery
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

### 使用 Docker

```dockerfile
# Dockerfile 示例
FROM python:3.9

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["celery", "-A", "src.app.core.celery_config.celery_app", "worker", "--loglevel=info", "--concurrency=1"]
```

## 性能优化

### Worker 配置
- 并发数设置为1，确保每分钟只处理一个批次
- 监控内存使用情况
- 设置合理的任务超时时间

### Redis 配置
- 启用持久化
- 设置内存限制
- 配置主从复制（高可用）

### 任务优化
- 避免长时间运行的任务
- 使用任务分片处理大量数据
- 实现任务重试机制

## 安全考虑

1. **Redis 安全**
   - 设置访问密码
   - 限制网络访问
   - 定期更新 Redis 版本

2. **任务安全**
   - 验证任务参数
   - 限制任务执行权限
   - 监控异常任务

3. **日志安全**
   - 避免记录敏感信息
   - 定期清理日志文件
   - 设置日志访问权限

## 系统优势

1. **简化设计**: 只有一个核心任务，易于维护和调试
2. **智能调度**: 自动选择最优执行顺序
3. **资源控制**: 避免系统过载，确保稳定性
4. **易于扩展**: 可以根据需要添加更多任务类型
