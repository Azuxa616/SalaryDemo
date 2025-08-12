-- 初始化项目表结构（PostgreSQL）

-- 确保 pgcrypto 扩展可用（用于生成UUID）
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

-- 项目表
CREATE TABLE IF NOT EXISTS public.projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- 约束条件
    CONSTRAINT projects_name_not_empty CHECK (name != '')
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_projects_name ON public.projects (name);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON public.projects (created_at);

-- 创建唯一索引确保项目名称不重复
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_name_unique ON public.projects (LOWER(name));

-- updated_at 自动更新时间戳触发器
CREATE OR REPLACE FUNCTION public.set_project_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_projects_set_updated_at ON public.projects;
CREATE TRIGGER trg_projects_set_updated_at
BEFORE UPDATE ON public.projects
FOR EACH ROW
EXECUTE PROCEDURE public.set_project_updated_at();

-- 添加表注释
COMMENT ON TABLE public.projects IS '项目表，用于存储项目基本信息';
COMMENT ON COLUMN public.projects.id IS '项目唯一ID，自动生成的UUID';
COMMENT ON COLUMN public.projects.name IS '项目名称，必填字段，不能为空';
COMMENT ON COLUMN public.projects.description IS '项目描述，可选字段';
COMMENT ON COLUMN public.projects.created_at IS '项目创建时间';
COMMENT ON COLUMN public.projects.updated_at IS '项目最后更新时间';

-- 插入一些示例项目数据（可选）
INSERT INTO public.projects (name, description) VALUES
    ('薪资管理系统', '员工薪资计算和管理系统'),
    ('考勤系统', '员工考勤记录和统计系统'),
    ('项目管理系统', '项目进度跟踪和任务分配系统')
ON CONFLICT DO NOTHING;
