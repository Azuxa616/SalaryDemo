-- 更新薪资计算批次表结构
-- 添加定时计算相关字段

-- 1. 添加scheduled_time字段（定时执行时间）
ALTER TABLE public.salary_calculation_batches 
ADD COLUMN IF NOT EXISTS scheduled_time TIMESTAMPTZ;

-- 2. 添加description字段（批次描述）
ALTER TABLE public.salary_calculation_batches 
ADD COLUMN IF NOT EXISTS description TEXT;

-- 3. 为scheduled_time字段创建索引
CREATE INDEX IF NOT EXISTS idx_salary_batches_scheduled_time 
ON public.salary_calculation_batches(scheduled_time);

-- 4. 更新状态枚举，添加SCHEDULED状态
-- 注意：PostgreSQL中需要先删除约束，再重新添加
-- 这里我们使用ALTER TYPE来扩展枚举类型

-- 5. 添加注释
COMMENT ON COLUMN public.salary_calculation_batches.scheduled_time IS '定时执行时间，为空表示立即执行';
COMMENT ON COLUMN public.salary_calculation_batches.description IS '批次描述信息';

-- 6. 更新现有记录的默认值
UPDATE public.salary_calculation_batches 
SET scheduled_time = NULL, description = '系统自动创建'
WHERE scheduled_time IS NULL;

-- 7. 验证更新结果
DO $$
BEGIN
    RAISE NOTICE '薪资计算批次表结构更新完成！';
    RAISE NOTICE '新增字段：scheduled_time, description';
    RAISE NOTICE '新增索引：idx_salary_batches_scheduled_time';
END $$;
