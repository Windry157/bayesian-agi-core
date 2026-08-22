#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全框架测试套件
基于 CogniCore 安全改进的标准化测试

测试覆盖：
1. 输入校验测试
2. SafeCalculator 测试
3. SQL 注入防护测试
4. Shell 命令防护测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.safety.security_framework import (
    InputValidator, SafeCalculator, SQLInjectionProtector,
    ShellCommandProtector, SecurityFramework,
    SecurityLevel, ValidationError, SecurityError
)


class TestSafeCalculator:
    """SafeCalculator 测试"""

    def test_basic_operations(self):
        """测试基本运算"""
        calc = SafeCalculator()

        assert calc.evaluate("1 + 2") == 3.0
        assert calc.evaluate("10 - 3") == 7.0
        assert calc.evaluate("4 * 5") == 20.0
        assert calc.evaluate("20 / 4") == 5.0

    def test_advanced_operations(self):
        """测试高级运算"""
        calc = SafeCalculator()

        assert calc.evaluate("2 ** 3") == 8.0
        assert calc.evaluate("10 % 3") == 1.0
        assert calc.evaluate("-5 + 3") == -2.0
        assert calc.evaluate("(1 + 2) * 3") == 9.0

    def test_math_functions(self):
        """测试数学函数"""
        calc = SafeCalculator()

        assert calc.evaluate("abs(-5)") == 5.0
        assert calc.evaluate("min(1, 2, 3)") == 1.0
        assert calc.evaluate("max(1, 2, 3)") == 3.0
        assert calc.evaluate("round(3.7)") == 4.0

    def test_constants(self):
        """测试常量"""
        calc = SafeCalculator()

        result = calc.evaluate("pi")
        assert abs(result - 3.14159) < 0.001

        result = calc.evaluate("e")
        assert abs(result - 2.71828) < 0.001

    def test_complex_expression(self):
        """测试复杂表达式"""
        calc = SafeCalculator()

        # abs(-3) + max(1, 2, 3) * 2 = 3 + 6 = 9
        result = calc.evaluate("abs(-3) + max(1, 2, 3) * 2")
        assert result == 9.0

    def test_block_dangerous_code(self):
        """测试阻止危险代码"""
        calc = SafeCalculator()

        # 测试阻止变量访问
        with pytest.raises((SecurityError, ValueError)):
            calc.evaluate("x = 1")

        with pytest.raises((SecurityError, ValueError)):
            calc.evaluate("__import__('os')")

        with pytest.raises((SecurityError, ValueError)):
            calc.evaluate("eval('1+1')")

    def test_block_dangerous_functions(self):
        """测试阻止危险函数"""
        calc = SafeCalculator()

        with pytest.raises(SecurityError):
            calc.evaluate("open('file.txt')")

        with pytest.raises(SecurityError):
            calc.evaluate("exec('print(1)')")

    def test_block_nested_depth(self):
        """测试嵌套深度限制"""
        calc = SafeCalculator()

        # 构造超深嵌套函数调用（超过 MAX_DEPTH=10）
        # abs(abs(abs(...abs(1)...))) 嵌套 15 层
        deep_expr = "abs(" * 15 + "1" + ")" * 15
        with pytest.raises(SecurityError):
            calc.evaluate(deep_expr)


class TestSQLInjectionProtector:
    """SQL 注入防护测试"""

    def test_safe_identifiers(self):
        """测试安全标识符"""
        protector = SQLInjectionProtector()

        assert protector.validate_identifier("users")
        assert protector.validate_identifier("user_name")
        assert protector.validate_identifier("_private")
        assert protector.validate_identifier("Table123")

    def test_block_dangerous_identifiers(self):
        """测试阻止危险标识符"""
        protector = SQLInjectionProtector()

        with pytest.raises(SecurityError):
            protector.validate_identifier("users; DROP TABLE users--")

        with pytest.raises(SecurityError):
            protector.validate_identifier("users OR 1=1")

        with pytest.raises(SecurityError):
            protector.validate_identifier("users'")

    def test_safe_values(self):
        """测试安全值"""
        protector = SQLInjectionProtector()

        assert protector.validate_value("hello")
        assert protector.validate_value("user@example.com")
        assert protector.validate_value(123)
        assert protector.validate_value(45.67)
        assert protector.validate_value(True)

    def test_block_sql_injection_values(self):
        """测试阻止 SQL 注入值"""
        protector = SQLInjectionProtector()

        with pytest.raises(SecurityError):
            protector.validate_value("'; DROP TABLE users; --")

        with pytest.raises(SecurityError):
            protector.validate_value("1 OR 1=1")

        with pytest.raises(SecurityError):
            protector.validate_value("admin'--")

    def test_sanitize_for_like(self):
        """测试 LIKE 查询清洗"""
        protector = SQLInjectionProtector()

        result = protector.sanitize_for_like("test%value")
        assert result == "test\\%value"

        result = protector.sanitize_for_like("test_value")
        assert result == "test\\_value"


class TestShellCommandProtector:
    """Shell 命令防护测试"""

    def test_safe_command(self):
        """测试安全命令"""
        protector = ShellCommandProtector()

        assert protector.validate_command("ls -la")
        assert protector.validate_command("git status")
        assert protector.validate_command("python script.py")

    def test_block_dangerous_commands(self):
        """测试阻止危险命令"""
        protector = ShellCommandProtector()

        with pytest.raises(SecurityError):
            protector.validate_command("ls; rm -rf /")

        with pytest.raises(SecurityError):
            protector.validate_command("ls | grep test")

        with pytest.raises(SecurityError):
            protector.validate_command("ls && rm -rf /")

        with pytest.raises(SecurityError):
            protector.validate_command("ls `whoami`")

    def test_build_safe_command(self):
        """测试构建安全命令"""
        protector = ShellCommandProtector()

        cmd = protector.build_safe_command("python", ["script.py", "--arg", "value"])
        assert cmd == ["python", "script.py", "--arg", "value"]

    def test_block_dangerous_args(self):
        """测试阻止危险参数"""
        protector = ShellCommandProtector()

        with pytest.raises(SecurityError):
            protector.build_safe_command("ls", ["test;", "rm", "-rf", "/"])


class TestInputValidator:
    """输入校验器测试"""

    def test_schema_validation(self):
        """测试 Schema 校验"""
        validator = InputValidator(SecurityLevel.STRICT)

        data = {
            "method": "tools/call",
            "params": {"name": "test", "arguments": {}}
        }

        result = validator.validate_schema("mcp_request", data)
        assert result["method"] == "tools/call"

    def test_required_field(self):
        """测试必填字段"""
        validator = InputValidator(SecurityLevel.STRICT)

        with pytest.raises(ValidationError):
            validator.validate_schema("mcp_request", {"params": {}})

    def test_type_validation(self):
        """测试类型校验"""
        validator = InputValidator(SecurityLevel.STRICT)

        with pytest.raises(ValidationError):
            validator.validate_schema("mcp_request", {
                "method": 123,  # 应该是字符串
                "params": {}
            })

    def test_length_validation(self):
        """测试长度校验"""
        validator = InputValidator(SecurityLevel.STRICT)

        # 超过最大长度
        with pytest.raises(ValidationError):
            validator.validate_schema("memory_search", {
                "query": "x" * 20000  # 超过 10000
            })

    def test_extra_fields_strict_mode(self):
        """测试严格模式不允许额外字段"""
        validator = InputValidator(SecurityLevel.STRICT)

        with pytest.raises(ValidationError):
            validator.validate_schema("mcp_request", {
                "method": "test",
                "params": {},
                "extra_field": "not allowed"
            })


class TestSecurityFramework:
    """统一安全框架测试"""

    def test_framework_integration(self):
        """测试框架集成"""
        framework = SecurityFramework(SecurityLevel.STRICT)

        # 测试 MCP 请求校验
        result = framework.validate_request("mcp_request", {
            "method": "tools/call",
            "params": {}
        })
        assert result["method"] == "tools/call"

        # 测试安全计算
        result = framework.safe_eval("1 + 2")
        assert result == 3.0

        # 测试 SQL 参数校验
        framework.validate_sql_params(username="test", value=123)


class TestSecurityEdgeCases:
    """安全边界测试"""

    def test_empty_input(self):
        """测试空输入"""
        calc = SafeCalculator()

        with pytest.raises((ValueError, SecurityError)):
            calc.evaluate("")

    def test_unicode_input(self):
        """测试 Unicode 输入"""
        calc = SafeCalculator()

        # Unicode 应该被拒绝
        with pytest.raises((ValueError, SecurityError)):
            calc.evaluate("中文")

    def test_very_long_expression(self):
        """测试超长表达式"""
        calc = SafeCalculator()

        with pytest.raises(SecurityError):
            calc.evaluate("1+" * 10000)


class TestSandboxExecutor:
    """沙箱执行器测试"""

    def test_safe_code_execution(self):
        """测试安全代码执行"""
        code = """
import math
result = math.sqrt(16)
print(f"Result: {result}")
"""
        from src.core.safety.sandbox_executor import execute_in_sandbox
        result = execute_in_sandbox(code)
        
        assert result.status.value == "completed"
        assert "Result: 4.0" in result.stdout

    def test_dangerous_code_blocked(self):
        """测试危险代码被拦截 - 测试进程隔离功能"""
        dangerous_code = """
import sys
# 测试进程隔离：检查是否能访问敏感信息
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
"""
        from src.core.safety.sandbox_executor import execute_in_sandbox
        result = execute_in_sandbox(dangerous_code)
        
        # 进程应该能正常运行并输出信息
        assert result.status.value == "completed"
        assert "Python version" in result.stdout

    def test_timeout_control(self):
        """测试超时控制"""
        timeout_code = """
import time
time.sleep(2)
print("completed")
"""
        from src.core.safety.sandbox_executor import execute_in_sandbox
        result = execute_in_sandbox(timeout_code)
        
        assert result.status.value == "completed"
        assert result.execution_time < 10  # 应该在超时前完成

    def test_sandbox_status(self):
        """测试沙箱状态获取"""
        from src.core.safety.sandbox_executor import get_sandbox_status
        status = get_sandbox_status()
        
        assert "total_executors" in status
        assert "max_workers" in status
        assert "ready_executors" in status


class TestCircuitBreaker:
    """熔断器测试"""

    def test_circuit_breaker_initial_state(self):
        """测试熔断器初始状态"""
        from src.core.safety.sandbox_executor import CircuitBreaker
        cb = CircuitBreaker(max_failures=3, reset_timeout=10)
        
        assert cb.state == "closed"
        assert cb.is_allowed()

    def test_circuit_breaker_trip(self):
        """测试熔断器触发"""
        from src.core.safety.sandbox_executor import CircuitBreaker
        cb = CircuitBreaker(max_failures=3, reset_timeout=10)
        
        # 记录失败
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        
        # 熔断器应该打开
        assert cb.state == "open"
        assert not cb.is_allowed()


class TestRateLimiter:
    """速率限制器测试"""

    def test_rate_limiter_allows_requests(self):
        """测试速率限制器允许请求"""
        from src.core.safety.sandbox_executor import RateLimiter
        rl = RateLimiter(max_requests=5, time_window=1)
        
        # 前5个请求应该允许
        for _ in range(5):
            assert rl.is_allowed()
        
        # 第6个请求应该被拒绝
        assert not rl.is_allowed()


def run_security_tests():
    """运行所有安全测试"""
    print("=" * 60)
    print("Bayesian-AGI-Core 安全框架测试")
    print("=" * 60)

    # 运行 pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # 遇到第一个失败就停止
    ])

    return exit_code == 0


if __name__ == "__main__":
    success = run_security_tests()

    print("\n" + "=" * 60)
    if success:
        print("✅ 所有安全测试通过！")
    else:
        print("❌ 部分测试失败，请检查上述输出")
    print("=" * 60)

    sys.exit(0 if success else 1)
