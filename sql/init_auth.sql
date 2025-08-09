-- 初始化用户鉴权相关表结构（PostgreSQL）

-- 如需使用 bcrypt 哈希（crypt('pwd', gen_salt('bf'))），请确保启用 pgcrypto
 CREATE SCHEMA IF NOT EXISTS public;
 -- 将 pgcrypto 安装到 public 模式，确保函数可解析
 CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

-- 用户表：role 范围 1~4（0 表示未登录，不入库）
CREATE TABLE IF NOT EXISTS public.users (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(255) UNIQUE,
    full_name     VARCHAR(255),
    password_hash TEXT         NOT NULL,
    role          SMALLINT     NOT NULL DEFAULT 2,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT users_role_check CHECK (role BETWEEN 1 AND 4)
);

CREATE INDEX IF NOT EXISTS idx_users_username ON public.users (username);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users (role);

-- updated_at 自动更新时间戳
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_set_updated_at ON public.users;
CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE PROCEDURE public.set_updated_at();

-- 预置超级管理员账号（默认密码：root，请部署后尽快修改）
 INSERT INTO public.users (username, email, full_name, password_hash, role, is_active)
 VALUES (
     'admin',
     'admin@example.com',
     'Super Administrator',
     public.crypt('root'::text, public.gen_salt('bf'::text)),
     4,
     TRUE
 )
 ON CONFLICT (username) DO NOTHING;


