import os

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg://postgres:root@localhost:5432/SalaryDemoDB'
)

# 应用地址配置（用于启动时输出访问地址）
APP_HOST: str = os.getenv('APP_HOST', '127.0.0.1')
APP_PORT: int = int(os.getenv('APP_PORT', '8000'))
BASE_URL: str = os.getenv('BASE_URL', f'http://{APP_HOST}:{APP_PORT}')