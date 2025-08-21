-- 薪资计算引擎数据库初始化脚本
-- 包含：表结构、索引、触发器、示例数据和注释

-- ========================================
-- 1. 创建表结构
-- ========================================

-- 1.1 薪资规则表
CREATE TABLE IF NOT EXISTS public.salary_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    rule_type       VARCHAR(20) NOT NULL CHECK (rule_type IN ('RATE', 'FIXED', 'CONDITIONAL')),
    formula         TEXT NOT NULL,
    variables       JSONB,
    conditions      JSONB,
    fixed_amount    DECIMAL(10,2),
    rate_multiplier DECIMAL(5,2),
    priority        INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT true,
    effective_from  DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to    DATE,
    department_id   INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT salary_rules_name_unique UNIQUE (name),
    CONSTRAINT salary_rules_effective_dates CHECK (effective_to IS NULL OR effective_from <= effective_to)
);

-- 1.2 计算批次表
CREATE TABLE IF NOT EXISTS public.salary_calculation_batches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_name      VARCHAR(255) NOT NULL,
    calculation_period VARCHAR(20) NOT NULL,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    total_employees INTEGER DEFAULT 0,
    processed_count INTEGER DEFAULT 0,
    success_count   INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    total_amount    DECIMAL(12,2) DEFAULT 0,
    error_log       TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_by      BIGINT NOT NULL REFERENCES public.users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT salary_batches_period_dates CHECK (period_start <= period_end)
);

-- 1.3 薪资计算结果表
CREATE TABLE IF NOT EXISTS public.salary_calculation_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id        UUID NOT NULL REFERENCES public.salary_calculation_batches(id),
    employee_id     BIGINT NOT NULL REFERENCES public.users(id),
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    base_salary     DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_hours     DECIMAL(6,2) NOT NULL DEFAULT 0,
    overtime_hours  DECIMAL(6,2) NOT NULL DEFAULT 0,
    rule_results    JSONB NOT NULL DEFAULT '{}',
    total_amount    DECIMAL(10,2) NOT NULL DEFAULT 0,
    deductions      JSONB NOT NULL DEFAULT '{}',
    net_amount      DECIMAL(10,2) NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'CALCULATED' CHECK (status IN ('CALCULATED', 'APPROVED', 'PAID', 'CANCELLED')),
    approved_by     BIGINT REFERENCES public.users(id),
    approved_at     TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT salary_results_period_dates CHECK (period_start <= period_end),
    CONSTRAINT salary_results_employee_period UNIQUE (employee_id, period_start, period_end)
);

-- 1.4 员工薪资配置表
CREATE TABLE IF NOT EXISTS public.employee_salary_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     BIGINT NOT NULL REFERENCES public.users(id),
    base_salary     DECIMAL(10,2) NOT NULL DEFAULT 0,
    hourly_rate     DECIMAL(8,2) NOT NULL DEFAULT 0,
    overtime_rate   DECIMAL(5,2) NOT NULL DEFAULT 1.5,
    department_id   INTEGER,
    position        VARCHAR(100),
    effective_from  DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to    DATE,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT employee_salary_effective_dates CHECK (effective_to IS NULL OR effective_from <= effective_from),
    CONSTRAINT employee_salary_employee_period UNIQUE (employee_id, effective_from)
);

-- 1.5 扣除项配置表
CREATE TABLE IF NOT EXISTS public.deduction_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    deduction_type  VARCHAR(20) NOT NULL CHECK (deduction_type IN ('PERCENTAGE', 'FIXED', 'CONDITIONAL')),
    percentage      DECIMAL(5,2),
    fixed_amount    DECIMAL(10,2),
    formula         TEXT,
    min_amount      DECIMAL(10,2) DEFAULT 0,
    max_amount      DECIMAL(10,2),
    is_active       BOOLEAN DEFAULT true,
    effective_from  DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT deduction_configs_effective_dates CHECK (effective_to IS NULL OR effective_from <= effective_to)
);

-- ========================================
-- 2. 创建索引
-- ========================================

-- 2.1 薪资规则表索引
CREATE INDEX IF NOT EXISTS idx_salary_rules_type_active ON public.salary_rules(rule_type, is_active);
CREATE INDEX IF NOT EXISTS idx_salary_rules_effective_dates ON public.salary_rules(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_salary_rules_department ON public.salary_rules(department_id);

-- 2.2 计算批次表索引
CREATE INDEX IF NOT EXISTS idx_salary_batches_status ON public.salary_calculation_batches(status);
CREATE INDEX IF NOT EXISTS idx_salary_batches_period ON public.salary_calculation_batches(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_salary_batches_created_by ON public.salary_calculation_batches(created_by);

-- 2.3 薪资计算结果表索引
CREATE INDEX IF NOT EXISTS idx_salary_results_batch ON public.salary_calculation_results(batch_id);
CREATE INDEX IF NOT EXISTS idx_salary_results_employee ON public.salary_calculation_results(employee_id);
CREATE INDEX IF NOT EXISTS idx_salary_results_period ON public.salary_calculation_results(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_salary_results_status ON public.salary_calculation_results(status);

-- 2.4 员工薪资配置表索引
CREATE INDEX IF NOT EXISTS idx_employee_salary_employee ON public.employee_salary_configs(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_salary_effective ON public.employee_salary_configs(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_employee_salary_active ON public.employee_salary_configs(is_active);

-- 2.5 扣除项配置表索引
CREATE INDEX IF NOT EXISTS idx_deduction_configs_active ON public.deduction_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_deduction_configs_effective ON public.deduction_configs(effective_from, effective_to);

-- ========================================
-- 3. 创建触发器和函数
-- ========================================

-- 3.1 更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 3.2 为各表创建更新时间触发器
CREATE TRIGGER update_salary_rules_updated_at BEFORE UPDATE ON public.salary_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_salary_batches_updated_at BEFORE UPDATE ON public.salary_calculation_batches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_salary_results_updated_at BEFORE UPDATE ON public.salary_calculation_results FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_employee_salary_updated_at BEFORE UPDATE ON public.employee_salary_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deduction_configs_updated_at BEFORE UPDATE ON public.deduction_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 4. 插入示例数据
-- ========================================

-- 4.1 插入示例薪资规则
INSERT INTO public.salary_rules (name, description, rule_type, formula, variables, priority) VALUES
('基本工资', '员工基本工资', 'FIXED', 'base_salary', '{"base_salary": "employee.base_salary"}', 1),
('工时费', '工时计算', 'RATE', 'hourly_rate * hours', '{"hours": "worklog.hours", "hourly_rate": "employee.hourly_rate"}', 2)
ON CONFLICT (name) DO NOTHING;

-- 4.2 插入示例扣除项配置
INSERT INTO public.deduction_configs (name, description, deduction_type, percentage, min_amount) VALUES
('个人所得税', '个人所得税扣除', 'PERCENTAGE', 3.0, 0),
('社保扣除', '社会保险扣除', 'PERCENTAGE', 8.0, 0),
('公积金', '住房公积金扣除', 'PERCENTAGE', 5.0, 0)
ON CONFLICT DO NOTHING;

-- ========================================
-- 5. 添加表和字段注释
-- ========================================

-- 5.1 表注释
COMMENT ON TABLE public.salary_rules IS '薪资规则表，支持三种规则类型：RATE(比率)、FIXED(固定)、CONDITIONAL(条件)';
COMMENT ON TABLE public.salary_calculation_batches IS '薪资计算批次表，记录每次计算的执行状态和结果';
COMMENT ON TABLE public.salary_calculation_results IS '薪资计算结果表，存储每个员工的详细薪资计算结果';
COMMENT ON TABLE public.employee_salary_configs IS '员工薪资配置表，存储员工的基本薪资信息';
COMMENT ON TABLE public.deduction_configs IS '扣除项配置表，定义各种扣除项的规则';

-- 5.2 字段注释
COMMENT ON COLUMN public.salary_rules.formula IS '规则计算公式，支持变量引用和基本运算';
COMMENT ON COLUMN public.salary_rules.variables IS '变量定义，JSON格式，定义公式中使用的变量来源';
COMMENT ON COLUMN public.salary_rules.conditions IS '条件规则，JSON格式，定义何时触发此规则';
COMMENT ON COLUMN public.salary_rules.priority IS '规则优先级，数字越小优先级越高，用于确定计算顺序';

COMMENT ON COLUMN public.salary_calculation_batches.status IS '计算状态：PENDING(待处理)、PROCESSING(处理中)、COMPLETED(已完成)、FAILED(失败)、CANCELLED(已取消)';
COMMENT ON COLUMN public.salary_calculation_batches.total_amount IS '本次计算的总金额';
COMMENT ON COLUMN public.salary_calculation_batches.error_log IS '错误日志，记录计算过程中的错误信息';

COMMENT ON COLUMN public.salary_calculation_results.rule_results IS '各规则计算结果，JSON格式存储每个规则的详细计算结果';
COMMENT ON COLUMN public.salary_calculation_results.deductions IS '扣除项详情，JSON格式存储各种扣除项的金额';
COMMENT ON COLUMN public.salary_calculation_results.net_amount IS '实发金额，扣除所有扣除项后的最终金额';

-- ========================================
-- 6. 初始化完成提示
-- ========================================

DO $$
BEGIN
    RAISE NOTICE '薪资计算引擎数据库初始化完成！';
    RAISE NOTICE '已创建 % 个表', (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'salary_%');
    RAISE NOTICE '已创建 % 个索引', (SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' AND tablename LIKE 'salary_%');
    RAISE NOTICE '已插入 % 条示例数据', (SELECT count(*) FROM public.salary_rules) + (SELECT count(*) FROM public.deduction_configs);
END $$;
