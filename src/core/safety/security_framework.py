#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全框架核心模块
Bayesian-AGI-Core 安全防护层

功能：
1. 统一输入校验框架（Validation Framework）
2. Schema 强制校验
3. 白名单验证器
4. 代码执行安全（替代 eval）
5. SQL 注入防护
"""

import ast
import re
import json
import operator
from typing import Any, Callable, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别枚举"""
    STRICT = "strict"       # 严格模式：所有输入必须通过校验
    MODERATE = "moderate"   # 中等模式：仅关键路径校验
    LENIENT = "lenient"     # 宽松模式：仅日志警告


@dataclass
class ValidationRule:
    """校验规则定义"""
    name: str
    validator: Callable[[Any], bool]
    error_message: str
    severity: str = "error"  # error, warning, info


@dataclass
class SchemaField:
    """Schema 字段定义"""
    name: str
    type: type
    required: bool = True
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[Any]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None
    error_message: Optional[str] = None


@dataclass
class Schema:
    """Schema 定义"""
    name: str
    fields: List[SchemaField]
    strict: bool = True  # 严格模式：不允许额外字段


class ValidationError(Exception):
    """校验错误"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"[{field}] {message}")


class SecurityError(Exception):
    """安全错误"""
    pass


class InputValidator:
    """统一输入校验器"""

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STRICT):
        self.security_level = security_level
        self.schemas: Dict[str, Schema] = {}
        self._register_default_schemas()
        logger.info(f"InputValidator 初始化完成，安全级别: {security_level.value}")

    def _register_default_schemas(self):
        """注册默认 Schema"""
        # MCP 请求 Schema
        self.register_schema(Schema(
            name="mcp_request",
            fields=[
                SchemaField(name="method", type=str, required=True, min_length=1),
                SchemaField(name="params", type=dict, required=False),
            ],
            strict=True
        ))

        # 工具调用 Schema
        self.register_schema(Schema(
            name="tool_call",
            fields=[
                SchemaField(name="name", type=str, required=True, min_length=1),
                SchemaField(name="arguments", type=dict, required=False),
            ],
            strict=True
        ))

        # 记忆搜索 Schema
        self.register_schema(Schema(
            name="memory_search",
            fields=[
                SchemaField(name="query", type=str, required=True, min_length=1, max_length=10000),
                SchemaField(name="top_k", type=int, required=False, min_value=1, max_value=100),
                SchemaField(name="layers", type=list, required=False),
            ],
            strict=False
        ))

    def register_schema(self, schema: Schema):
        """注册 Schema"""
        self.schemas[schema.name] = schema
        logger.info(f"注册 Schema: {schema.name}")

    def validate_schema(self, schema_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """根据 Schema 校验数据"""
        if schema_name not in self.schemas:
            if self.security_level == SecurityLevel.STRICT:
                raise ValidationError("schema", f"未知 Schema: {schema_name}")
            logger.warning(f"未知 Schema: {schema_name}")
            return data

        schema = self.schemas[schema_name]
        validated_data = {}
        errors = []

        for field_def in schema.fields:
            value = data.get(field_def.name)

            # 必填字段检查
            if field_def.required and value is None:
                errors.append(ValidationError(field_def.name, "必填字段不能为空"))
                continue

            if value is None:
                validated_data[field_def.name] = None
                continue

            # 类型检查
            if not isinstance(value, field_def.type) and field_def.type != Any:
                errors.append(ValidationError(
                    field_def.name,
                    field_def.error_message or f"类型错误，期望 {field_def.type.__name__}",
                    value
                ))
                continue

            # 数值范围检查
            if isinstance(value, (int, float)):
                if field_def.min_value is not None and value < field_def.min_value:
                    errors.append(ValidationError(
                        field_def.name,
                        field_def.error_message or f"值必须 >= {field_def.min_value}",
                        value
                    ))
                if field_def.max_value is not None and value > field_def.max_value:
                    errors.append(ValidationError(
                        field_def.name,
                        field_def.error_message or f"值必须 <= {field_def.max_value}",
                        value
                    ))

            # 字符串长度检查
            if isinstance(value, str):
                if field_def.min_length is not None and len(value) < field_def.min_length:
                    errors.append(ValidationError(
                        field_def.name,
                        field_def.error_message or f"长度必须 >= {field_def.min_length}",
                        value
                    ))
                if field_def.max_length is not None and len(value) > field_def.max_length:
                    errors.append(ValidationError(
                        field_def.name,
                        field_def.error_message or f"长度必须 <= {field_def.max_length}",
                        value
                    ))
                if field_def.pattern is not None:
                    if not re.match(field_def.pattern, value):
                        errors.append(ValidationError(
                            field_def.name,
                            field_def.error_message or f"格式不匹配: {field_def.pattern}",
                            value
                        ))

            # 枚举值检查
            if field_def.enum_values is not None:
                if value not in field_def.enum_values:
                    errors.append(ValidationError(
                        field_def.name,
                        field_def.error_message or f"值必须在 {field_def.enum_values} 中",
                        value
                    ))

            # 自定义校验器
            if field_def.custom_validator is not None:
                try:
                    if not field_def.custom_validator(value):
                        errors.append(ValidationError(
                            field_def.name,
                            field_def.error_message or "自定义校验失败",
                            value
                        ))
                except Exception as e:
                    errors.append(ValidationError(field_def.name, f"校验异常: {str(e)}", value))

            validated_data[field_def.name] = value

        # 严格模式：不允许额外字段
        if schema.strict and self.security_level == SecurityLevel.STRICT:
            extra_fields = set(data.keys()) - set(f.name for f in schema.fields)
            if extra_fields:
                errors.append(ValidationError(
                    "_extra_fields",
                    f"不允许的字段: {extra_fields}"
                ))

        if errors:
            if self.security_level == SecurityLevel.STRICT:
                raise errors[0]
            else:
                for err in errors:
                    logger.warning(f"校验警告: {err}")

        return validated_data

    def validate(self, data: Any, rules: List[ValidationRule]) -> bool:
        """通用校验方法"""
        for rule in rules:
            try:
                if not rule.validator(data):
                    if rule.severity == "error":
                        raise ValidationError(rule.name, rule.error_message, data)
                    logger.warning(f"[{rule.severity.upper()}] {rule.name}: {rule.error_message}")
            except ValidationError:
                raise
            except Exception as e:
                logger.error(f"校验异常: {rule.name} - {e}")
                if rule.severity == "error":
                    raise ValidationError(rule.name, str(e), data)
        return True


class SafeCalculator:
    """
    安全计算器 - 替代 eval()
    使用 AST 白名单解析数学表达式
    """

    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: lambda x: x,
        ast.Mod: operator.mod,
    }

    ALLOWED_FUNCTIONS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'len': len,
    }

    MAX_DEPTH = 10

    def __init__(self):
        self._allowed_nodes = (ast.BinOp, ast.UnaryOp, ast.Name, ast.Constant, ast.Call)
        logger.info("SafeCalculator 初始化完成，AST 白名单计算器已启用")

    def _eval_node(self, node: ast.AST, depth: int = 0) -> Any:
        """递归评估 AST 节点"""
        if depth > self.MAX_DEPTH:
            raise SecurityError("表达式嵌套深度超限")

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise SecurityError(f"不支持的常量类型: {type(node.value)}")

        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                if node.id == 'pi':
                    return 3.141592653589793
                if node.id == 'e':
                    return 2.718281828459045
                raise SecurityError(f"不允许的变量: {node.id}")
            raise SecurityError(f"不支持的上下文: {type(node.ctx)}")

        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, depth + 1)
            right = self._eval_node(node.right, depth + 1)
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPERATORS:
                raise SecurityError(f"不支持的操作符: {op_type.__name__}")
            return self.ALLOWED_OPERATORS[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, depth + 1)
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPERATORS:
                raise SecurityError(f"不支持的一元操作符: {op_type.__name__}")
            return self.ALLOWED_OPERATORS[op_type](operand)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name not in self.ALLOWED_FUNCTIONS:
                    raise SecurityError(f"不允许的函数: {func_name}")
                args = [self._eval_node(arg, depth + 1) for arg in node.args]
                return self.ALLOWED_FUNCTIONS[func_name](*args)
            raise SecurityError("不支持的函数调用")

        raise SecurityError(f"不支持的 AST 节点: {type(node).__name__}")

    def evaluate(self, expression: str) -> float:
        """
        安全评估数学表达式

        Args:
            expression: 数学表达式字符串

        Returns:
            计算结果

        Raises:
            SecurityError: 安全错误
            ValueError: 表达式错误
        """
        if not isinstance(expression, str):
            raise SecurityError("表达式必须是字符串")

        if len(expression) > 1000:
            raise SecurityError("表达式长度超限")

        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise ValueError(f"语法错误: {e}")

        return self._eval_node(tree.body)


class SQLInjectionProtector:
    """
    SQL 注入防护器
    基于白名单的参数化查询
    """

    DANGEROUS_PATTERNS = [
        r"(\bOR\b|\bAND\b).*=.*",  # OR/AND 注入
        r"(--|;|/\*|\*/)",          # 注释注入
        r"(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b)",  # 关键词注入
        r"('|\"|;)",                 # 引号/分号注入
        r"(\bEXEC\b|\bEXECUTE\b|\bXP_)",  # 存储过程注入
    ]

    SAFE_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    SAFE_VALUE_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\s]+$')

    def __init__(self):
        self.dangerous_patterns = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS]
        logger.info("SQL注入防护器初始化完成，白名单模式已启用")

    def validate_identifier(self, identifier: str) -> bool:
        """
        校验 SQL 标识符（表名、列名）

        Args:
            identifier: 标识符

        Returns:
            是否安全

        Raises:
            SecurityError: 安全错误
        """
        if not identifier:
            raise SecurityError("标识符不能为空")

        if not isinstance(identifier, str):
            raise SecurityError("标识符必须是字符串")

        if not self.SAFE_IDENTIFIER_PATTERN.match(identifier):
            raise SecurityError(f"不允许的标识符格式: {identifier}")

        if len(identifier) > 64:
            raise SecurityError("标识符长度超限")

        # 检查危险模式
        for pattern in self.dangerous_patterns:
            if pattern.search(identifier):
                raise SecurityError(f"标识符包含危险模式: {pattern.pattern}")

        return True

    def validate_value(self, value: Any) -> bool:
        """
        校验 SQL 值

        Args:
            value: 值

        Returns:
            是否安全

        Raises:
            SecurityError: 安全错误
        """
        if value is None:
            return True

        if isinstance(value, (int, float, bool)):
            return True

        if isinstance(value, str):
            if len(value) > 10000:
                raise SecurityError("值长度超限")

            # 检查危险模式
            for pattern in self.dangerous_patterns:
                if pattern.search(value):
                    raise SecurityError(f"值包含危险模式: {pattern.pattern}")

            return True

        if isinstance(value, (list, tuple)):
            for item in value:
                self.validate_value(item)
            return True

        if isinstance(value, dict):
            for k, v in value.items():
                self.validate_identifier(k)
                self.validate_value(v)
            return True

        raise SecurityError(f"不支持的值类型: {type(value)}")

    def sanitize_for_like(self, value: str) -> str:
        """
        清洗 LIKE 查询的值

        Args:
            value: 原始值

        Returns:
            清洗后的值
        """
        if not isinstance(value, str):
            raise SecurityError("LIKE 值必须是字符串")

        # 转义特殊字符
        value = value.replace('\\', '\\\\')
        value = value.replace('%', '\\%')
        value = value.replace('_', '\\_')

        return value


class ShellCommandProtector:
    """
    Shell 命令防护器
    防止 shell 注入
    """

    SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_\-./=:\s]+$')
    DANGEROUS_CHARS = [';', '|', '&', '`', '$', '(', ')', '<', '>', '\n', '\r']

    def __init__(self):
        logger.info("Shell 命令防护器初始化完成")

    def validate_command(self, command: str) -> bool:
        """
        校验 Shell 命令

        Args:
            command: 命令字符串

        Returns:
            是否安全

        Raises:
            SecurityError: 安全错误
        """
        if not command:
            raise SecurityError("命令不能为空")

        if not isinstance(command, str):
            raise SecurityError("命令必须是字符串")

        if len(command) > 10000:
            raise SecurityError("命令长度超限")

        # 检查危险字符
        for char in self.DANGEROUS_CHARS:
            if char in command:
                raise SecurityError(f"命令包含危险字符: {repr(char)}")

        return True

    def build_safe_command(self, base_command: str, args: List[str]) -> List[str]:
        """
        构建安全的命令参数列表

        Args:
            base_command: 基础命令
            args: 参数列表

        Returns:
            安全的命令列表

        Raises:
            SecurityError: 安全错误
        """
        # 验证基础命令
        parts = base_command.split()
        if not parts:
            raise SecurityError("基础命令不能为空")

        safe_command = [parts[0]]

        # 验证并添加每个参数
        for arg in args:
            if not isinstance(arg, str):
                raise SecurityError("所有参数必须是字符串")
            if not arg:
                continue

            # 检查危险字符
            for char in self.DANGEROUS_CHARS:
                if char in arg:
                    raise SecurityError(f"参数包含危险字符: {repr(char)}")

            safe_command.append(arg)

        return safe_command


class SecurityFramework:
    """
    统一安全框架
    整合所有安全组件
    
    四层防御模型:
    L1: 进程隔离 - subprocess/Popen 进程级隔离
    L2: 资源限制 - CPU/内存/时间限制
    L3: 系统调用控制 - 白名单机制
    L4: 网络隔离 - 出站控制
    """

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STRICT):
        self.security_level = security_level
        self.validator = InputValidator(security_level)
        self.calculator = SafeCalculator()
        self.sql_protector = SQLInjectionProtector()
        self.shell_protector = ShellCommandProtector()
        
        # 延迟导入沙箱执行器，避免循环依赖
        from .sandbox_executor import SandboxManager
        self.sandbox_manager = SandboxManager(max_workers=10)
        
        logger.info(f"SecurityFramework 初始化完成，安全级别: {security_level.value}")
        logger.info("四层防御模型已启用: L1(进程隔离) L2(资源限制) L3(系统调用) L4(网络隔离)")

    def validate_request(self, schema_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """校验请求"""
        return self.validator.validate_schema(schema_name, data)

    def safe_eval(self, expression: str) -> float:
        """安全评估表达式"""
        return self.calculator.evaluate(expression)

    def validate_sql_params(self, **params) -> bool:
        """校验 SQL 参数"""
        return self.sql_protector.validate_value(params)

    def build_shell_command(self, base_command: str, args: List[str]) -> List[str]:
        """构建安全的 Shell 命令"""
        return self.shell_protector.build_safe_command(base_command, args)

    def execute_in_sandbox(self, code: str, language: str = "python") -> dict:
        """
        在沙箱中执行代码
        
        Args:
            code: 要执行的代码
            language: 代码语言 (python, javascript, shell)
        
        Returns:
            执行结果字典
        """
        result = self.sandbox_manager.execute(code, language)
        return {
            "status": result.status.value,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.return_code,
            "execution_time": result.execution_time,
            "error_message": result.error_message
        }

    def get_sandbox_status(self) -> dict:
        """获取沙箱状态"""
        return self.sandbox_manager.get_status()

    def get_security_metrics(self) -> dict:
        """获取所有安全指标"""
        return {
            "security_level": self.security_level.value,
            "sandbox_status": self.sandbox_manager.get_status()
        }


# 全局安全框架实例
security_framework = SecurityFramework(security_level=SecurityLevel.STRICT)


def validate_mcp_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    校验 MCP 请求
    入口函数
    """
    return security_framework.validate_request("mcp_request", data)


def validate_tool_call(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    校验工具调用
    入口函数
    """
    return security_framework.validate_request("tool_call", data)


def safe_calculate(expression: str) -> float:
    """
    安全计算表达式
    替代 eval()
    """
    return security_framework.safe_eval(expression)
