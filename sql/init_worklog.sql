-- 初始化工作记录表结构（PostgreSQL）

-- 确保 pgcrypto 扩展可用（用于生成UUID）
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

-- 工作记录表
CREATE TABLE IF NOT EXISTS public.worklogs (
    entry_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id   BIGINT NOT NULL,
    date          DATE NOT NULL,
    project_id    UUID NOT NULL,
    task_type     VARCHAR(50) NOT NULL,
    hours         DECIMAL(4,2) NOT NULL,
    remarks       TEXT,
    status        SMALLINT NOT NULL DEFAULT 0,
    ext_field     VARCHAR(50),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- 约束条件
    CONSTRAINT worklogs_hours_check CHECK (hours > 0 AND hours <= 24),
    CONSTRAINT worklogs_date_check CHECK (date <= CURRENT_DATE),
    CONSTRAINT worklogs_status_check CHECK (status IN (0, 1, 2))
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_worklogs_employee_id ON public.worklogs (employee_id);
CREATE INDEX IF NOT EXISTS idx_worklogs_date ON public.worklogs (date);
CREATE INDEX IF NOT EXISTS idx_worklogs_project_id ON public.worklogs (project_id);
CREATE INDEX IF NOT EXISTS idx_worklogs_task_type ON public.worklogs (task_type);
CREATE INDEX IF NOT EXISTS idx_worklogs_status ON public.worklogs (status);
CREATE INDEX IF NOT EXISTS idx_worklogs_ext_field ON public.worklogs (ext_field);

-- 创建复合索引用于常见查询场景
CREATE INDEX IF NOT EXISTS idx_worklogs_employee_date ON public.worklogs (employee_id, date);
CREATE INDEX IF NOT EXISTS idx_worklogs_project_date ON public.worklogs (project_id, date);

-- 添加外键约束（注意：这里假设users和projects表已存在）
-- 如果表不存在，请先创建相应的表，然后取消注释以下约束

ALTER TABLE public.worklogs 
    ADD CONSTRAINT fk_worklogs_employee 
    FOREIGN KEY (employee_id) REFERENCES public.users(id);

ALTER TABLE public.worklogs 
    ADD CONSTRAINT fk_worklogs_project 
    FOREIGN KEY (project_id) REFERENCES public.projects(id);

-- updated_at 自动更新时间戳触发器
CREATE OR REPLACE FUNCTION public.set_worklog_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_worklogs_set_updated_at ON public.worklogs;
CREATE TRIGGER trg_worklogs_set_updated_at
BEFORE UPDATE ON public.worklogs
FOR EACH ROW
EXECUTE PROCEDURE public.set_worklog_updated_at();

-- 添加表注释
COMMENT ON TABLE public.worklogs IS '工作记录表，用于存储员工的工作时间和任务信息';
COMMENT ON COLUMN public.worklogs.entry_id IS '记录唯一ID，自动生成的UUID';
COMMENT ON COLUMN public.worklogs.employee_id IS '员工ID，关联用户表(users.id)';
COMMENT ON COLUMN public.worklogs.date IS '工作日期，不能超过当前日期';
COMMENT ON COLUMN public.worklogs.project_id IS '项目ID，关联项目表(projects.id)';
COMMENT ON COLUMN public.worklogs.task_type IS '任务类型，如开发、测试、文档等';
COMMENT ON COLUMN public.worklogs.hours IS '工时，范围0.01-24小时';
COMMENT ON COLUMN public.worklogs.remarks IS '备注信息，可选字段';
COMMENT ON COLUMN public.worklogs.status IS '核算状态：0=待核算，1=已核算，2=保留状态';
COMMENT ON COLUMN public.worklogs.ext_field IS '扩展字段，用于日后迭代开发，可选';
COMMENT ON COLUMN public.worklogs.created_at IS '记录创建时间';
COMMENT ON COLUMN public.worklogs.updated_at IS '记录最后更新时间';
