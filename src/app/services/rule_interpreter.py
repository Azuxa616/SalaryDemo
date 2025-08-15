"""
薪资规则解释器引擎
负责解析和执行薪资计算规则
"""
import re
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class RuleInterpreter:
    """薪资规则解释器"""
    
    def __init__(self):
        self.supported_operators = {
            '+': lambda x, y: x + y,
            '-': lambda x, y: x - y,
            '*': lambda x, y: x * y,
            '/': lambda x, y: x / y if y != 0 else 0,
        }
    
    def evaluate_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行规则计算"""
        try:
            rule_type = rule.get('rule_type')
            formula = rule.get('formula')
            
            if rule_type == 'FIXED':
                return self._evaluate_fixed_rule(rule, context)
            elif rule_type == 'RATE':
                return self._evaluate_rate_rule(rule, context)
            elif rule_type == 'CONDITIONAL':
                return self._evaluate_conditional_rule(rule, context)
            else:
                return {'amount': 0, 'error': f'不支持的规则类型: {rule_type}'}
                
        except Exception as e:
            logger.error(f"规则执行失败: {rule.get('name', 'Unknown')}, 错误: {str(e)}")
            return {'amount': 0, 'error': str(e)}
    
    def _evaluate_fixed_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行固定金额规则"""
        try:
            amount = rule.get('fixed_amount', 0)
            if amount is None:
                # 尝试从公式中提取数字
                numbers = re.findall(r'\b\d+\.?\d*\b', rule['formula'])
                amount = Decimal(numbers[0]) if numbers else 0
            
            return {
                'amount': Decimal(str(amount)),
                'rule_name': rule.get('name', ''),
                'rule_type': 'FIXED',
                'result': f"固定金额: {amount}"
            }
        except Exception as e:
            return {'amount': 0, 'error': f'固定规则执行失败: {str(e)}'}
    
    def _evaluate_rate_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行比率规则"""
        try:
            # 解析公式中的变量
            variables = self._extract_variables(rule['formula'])
            
            # 获取变量值
            var_values = {}
            for var in variables:
                value = self._get_variable_value(var, context)
                if value is not None:
                    var_values[var] = value
            
            # 执行计算
            result = self._execute_formula(rule['formula'], var_values)
            
            return {
                'amount': result,
                'rule_name': rule.get('name', ''),
                'rule_type': 'RATE',
                'variables': var_values,
                'result': f"比率计算: {result}"
            }
        except Exception as e:
            return {'amount': 0, 'error': f'比率规则执行失败: {str(e)}'}
    
    def _evaluate_conditional_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行条件规则"""
        try:
            conditions = rule.get('conditions', {})
            
            # 检查条件是否满足
            if not self._check_conditions(conditions, context):
                return {
                    'amount': 0,
                    'rule_name': rule.get('name', ''),
                    'rule_type': 'CONDITIONAL',
                    'result': '条件不满足'
                }
            
            # 执行条件满足后的计算
            variables = self._extract_variables(rule['formula'])
            var_values = {}
            for var in variables:
                value = self._get_variable_value(var, context)
                if value is not None:
                    var_values[var] = value
            
            result = self._execute_formula(rule['formula'], var_values)
            
            return {
                'amount': result,
                'rule_name': rule.get('name', ''),
                'rule_type': 'CONDITIONAL',
                'result': f"条件满足，计算结果: {result}"
            }
        except Exception as e:
            return {'amount': 0, 'error': f'条件规则执行失败: {str(e)}'}
    
    def _extract_variables(self, formula: str) -> List[str]:
        """提取公式中的变量"""
        variables = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_.]*\b', formula)
        # 过滤掉函数名
        functions = ['max', 'min', 'abs', 'round', 'IF', 'THEN', 'ELSE']
        return [var for var in variables if var not in functions]
    
    def _get_variable_value(self, variable: str, context: Dict[str, Any]) -> Optional[Any]:
        """获取变量值"""
        try:
            parts = variable.split('.')
            value = context
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            
            return value
        except:
            return None
    
    def _check_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """检查条件是否满足"""
        if not conditions:
            return True
        
        try:
            for condition_key, condition_value in conditions.items():
                if not self._evaluate_condition(condition_key, condition_value, context):
                    return False
            return True
        except Exception as e:
            logger.error(f"条件检查失败: {str(e)}")
            return False
    
    def _evaluate_condition(self, key: str, value: Any, context: Dict[str, Any]) -> bool:
        """评估单个条件"""
        try:
            actual_value = self._get_variable_value(key, context)
            if actual_value is None:
                return False
            
            if isinstance(value, str):
                if '>' in value:
                    threshold = self._extract_threshold(value, '>')
                    return actual_value > threshold
                elif '<' in value:
                    threshold = self._extract_threshold(value, '<')
                    return actual_value < threshold
                else:
                    return str(actual_value) == str(value)
            
            return actual_value == value
        except Exception as e:
            logger.error(f"条件评估失败: {key}={value}, 错误: {str(e)}")
            return False
    
    def _extract_threshold(self, condition: str, operator: str) -> Any:
        """提取条件中的阈值"""
        try:
            parts = condition.split(operator)
            if len(parts) > 1:
                threshold_str = parts[1].strip()
                if '.' in threshold_str:
                    return float(threshold_str)
                else:
                    return int(threshold_str)
            return 0
        except:
            return 0
    
    def _execute_formula(self, formula: str, variables: Dict[str, Any]) -> Decimal:
        """执行公式计算"""
        try:
            expression = formula
            for var_name, var_value in variables.items():
                if isinstance(var_value, (int, float, Decimal)):
                    expression = expression.replace(var_name, str(var_value))
            
            result = eval(expression, {"__builtins__": {}}, {})
            return Decimal(str(result))
        except Exception as e:
            logger.error(f"公式执行失败: {formula}, 错误: {str(e)}")
            return Decimal('0')
