@echo off
chcp 65001 >nul
title 薪资计算系统服务启动器

echo ========================================
echo 💰 薪资计算系统服务启动器
echo ========================================
echo.
echo 📋 系统说明:
echo   - 每分钟检查一次待执行的定时批次
echo   - 每次只处理一个最早到达核算时间的批次
echo   - 确保系统稳定性和资源控制
echo.
echo ========================================

echo 🔍 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装或未添加到 PATH
    pause
    exit /b 1
)
echo ✅ Python 环境正常

echo.
echo 🔍 检查 Redis 服务...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Redis 服务未启动，正在启动...
    start "Redis Server" redis-server
    timeout /t 3 /nobreak >nul
) else (
    echo ✅ Redis 服务正常
)

echo.
echo 🚀 启动 FastAPI 应用...
start "FastAPI App" cmd /k "python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000 --log-level debug"

echo.
echo ⏰ 启动定时任务系统...
start "Celery Worker" cmd /k "celery -A src.app.core.celery_config.celery_app worker --loglevel=info --concurrency=1"
timeout /t 3 /nobreak >nul
start "Celery Beat" cmd /k "celery -A src.app.core.celery_config.celery_app beat --loglevel=info"

echo.
echo ========================================
echo 🎉 所有服务启动完成！
echo ========================================
echo.
echo 📱 FastAPI 应用: http://127.0.0.1:8000
echo 📚 API 文档: http://127.0.0.1:8000/docs
echo ⏰ 定时任务: 已启动 Worker 和 Beat
echo.
echo 💡 系统特性:
echo   • 每分钟自动检查待执行批次
echo   • 智能选择最早到达核算时间的批次
echo   • 每分钟最多处理一个批次，确保稳定性
echo.
echo 💡 提示：
echo   - 关闭窗口即可停止对应服务
echo   - 查看日志了解服务运行状态
echo   - 访问 /docs 查看 API 接口
echo.
pause
