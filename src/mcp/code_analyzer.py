import re
import math
from collections import Counter
from typing import Any, Dict, List


class CodeAnalyzer:
    @staticmethod
    def cyclomatic_complexity(code: str, language: str = "python") -> int:
        decision_keywords = {
            "python": [r'\bif\b', r'\belif\b', r'\bwhile\b', r'\bfor\b', r'\band\b', r'\bor\b', r'\bexcept\b', r'\bcase\b', r'\bassert\b'],
            "javascript": [r'\bif\b', r'\belse if\b', r'\bwhile\b', r'\bfor\b', r'\bcase\b', r'\bcatch\b', r'\b\?\b', r'\b\|\|\b', r'\b&&\b', r'\bswitch\b'],
            "typescript": [r'\bif\b', r'\belse if\b', r'\bwhile\b', r'\bfor\b', r'\bcase\b', r'\bcatch\b', r'\b\?\b', r'\b\|\|\b', r'\b&&\b', r'\bswitch\b'],
            "java": [r'\bif\b', r'\belse if\b', r'\bwhile\b', r'\bfor\b', r'\bcase\b', r'\bcatch\b', r'\bswitch\b', r'\b\&\&\b', r'\b\|\|\b'],
            "go": [r'\bif\b', r'\belse if\b', r'\bwhile\b', r'\bfor\b', r'\bcase\b', r'\bcatch\b', r'\bswitch\b', r'\b\&\&\b', r'\b\|\|\b'],
            "rust": [r'\bif\b', r'\belse if\b', r'\bwhile\b', r'\bfor\b', r'\bcase\b', r'\bcatch\b', r'\bswitch\b', r'\b\&\&\b', r'\b\|\|\b'],
        }
        kws = decision_keywords.get(language, [r'\bif\b', r'\bwhile\b', r'\bfor\b', r'\bcase\b'])
        code_clean = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        code_clean = re.sub(r'""".*?"""', '', code_clean, flags=re.DOTALL)
        code_clean = re.sub(r"'''.*?'''", '', code_clean, flags=re.DOTALL)
        code_clean = re.sub(r'//.*$', '', code_clean, flags=re.MULTILINE)
        code_clean = re.sub(r'/\*.*?\*/', '', code_clean, flags=re.DOTALL)
        complexity = 1
        for kw in kws:
            matches = re.findall(kw, code_clean)
            complexity += len(matches)
        return complexity

    @staticmethod
    def cognitive_complexity(code: str, language: str = "python") -> int:
        cognitive = 0
        nesting = 0
        lines = code.split('\n')
        indent_stack = [0]
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(('#', '//', '/*', '*', '"""', "'''")):
                continue
            indent = len(line) - len(line.lstrip())
            while indent_stack and indent < indent_stack[-1]:
                indent_stack.pop()
                nesting = max(0, nesting - 1)
            if indent_stack and indent > indent_stack[-1]:
                indent_stack.append(indent)
                nesting += 1
            if re.search(r'\b(if|while|for|catch|case)\b', stripped):
                cognitive += 1 + nesting
            elif re.search(r'\b(elif|else if)\b', stripped):
                cognitive += 1 + max(0, nesting - 1)
            elif re.search(r'\b(and|or|&&|\|\|)\b', stripped):
                cognitive += 1
            elif '?' in stripped and ':' in stripped:
                cognitive += 1 + nesting
        return cognitive

    @staticmethod
    def halstead_metrics(code: str, language: str = "python") -> Dict[str, float]:
        if language == "python":
            operators_set = {
                '+', '-', '*', '/', '//', '%', '**', '<<', '>>', '&', '|', '^', '~',
                '<', '>', '<=', '>=', '==', '!=', '=', '+=', '-=', '*=', '/=', '%=',
                'and', 'or', 'not', 'in', 'is', 'if', 'else', 'elif', 'for', 'while',
                'def', 'class', 'return', 'yield', 'import', 'from', 'as', 'with',
                'try', 'except', 'finally', 'raise', 'assert', 'break', 'continue',
                'lambda', 'del', 'global', 'nonlocal', 'pass'
            }
        else:
            operators_set = {'+', '-', '*', '/', '%', '=', '==', '!=', '<', '>', '<=', '>=', '&&', '||', '!'}
        identifiers = set(re.findall(r'\b[a-zA-Z_$]\w*\b', code))
        ops_in_code = {t for t in re.findall(r'(?:\|\||&&|[+\-*/%]=?|<<|>>|[&|^~<>!=]=?|\b\w+\b)', code) if t in operators_set}
        n1 = len(ops_in_code)
        n2 = len(identifiers)
        all_tokens = re.findall(r'\b\w+\b|[^\w\s]', code)
        n1_total = sum(1 for t in all_tokens if t in operators_set)
        n2_total = len(all_tokens) - n1_total
        if n1 == 0 or n2 == 0:
            return {"vocabulary": 0, "length": 0, "volume": 0, "difficulty": 0, "effort": 0}
        vocabulary = n1 + n2
        length = n1_total + n2_total
        volume = length * math.log2(vocabulary) if vocabulary > 0 else 0
        difficulty = (n1 / 2) * (n2_total / max(n2, 1))
        effort = difficulty * volume
        return {
            "vocabulary": vocabulary,
            "length": length,
            "volume": round(volume, 1),
            "difficulty": round(difficulty, 2),
            "effort": round(effort, 1)
        }

    @staticmethod
    def detect_issues(code: str, language: str = "python") -> List[Dict[str, Any]]:
        issues = []
        if re.search(r'\bwhile\s+True\b', code) and 'break' not in code:
            if 'time.sleep' not in code:
                issues.append({"type": "infinite_loop", "severity": "critical", "message": "潜在死循环（while True 缺少 break 或 sleep）"})
        if re.search(r'\b(connect|open|socket)\s*\(', code):
            if not re.search(r'\b(close|release|disconnect)\b', code):
                issues.append({"type": "resource_leak", "severity": "high", "message": "资源未显式关闭（连接/文件/套接字）"})
        if re.search(r'f["\'].*execute|execute.*f["\']', code) or re.search(r'\+\s*["\'].*execute|execute.*\s*\+', code):
            issues.append({"type": "sql_injection", "severity": "critical", "message": "SQL 注入风险（使用字符串拼接构建查询）"})
        if re.search(r'\b(open|connect|read|write|delete|remove)\s*\(', code):
            if not re.search(r'\btry\b', code):
                issues.append({"type": "missing_error_handling", "severity": "medium", "message": "缺少异常处理"})
        func_lines = re.findall(r'def\s+\w+.*?:(.*?)(?=\n\S|\Z)', code, re.DOTALL)
        for func in func_lines:
            line_count = len(func.strip().split('\n'))
            if line_count > 50:
                issues.append({"type": "long_function", "severity": "low", "message": f"函数过长（{line_count} 行），建议拆分"})
        lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
        line_counts = Counter(lines)
        for line, count in line_counts.items():
            if count >= 3 and len(line) > 20:
                issues.append({"type": "duplicate_code", "severity": "low", "message": f"重复代码（出现 {count} 次）：{line[:50]}..."})
                break
        if re.search(r'(password|secret|api_key|token)\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            issues.append({"type": "hardcoded_secret", "severity": "critical", "message": "存在硬编码密码或密钥"})
        return issues
