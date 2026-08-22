#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码分析模块 - OpenCode核心能力
"""

import ast
import json
from typing import List, Dict, Any, Optional
import subprocess
import tempfile
import os

class CodeAnalyzer:
    """代码分析器"""
    
    @staticmethod
    def analyze_complexity(code: str) -> Dict[str, Any]:
        try:
            tree = ast.parse(code)
            complexity = {
                'cyclomatic_complexity': CodeAnalyzer._calculate_cyclomatic_complexity(tree),
                'loc': len(code.splitlines()),
                'functions': CodeAnalyzer._count_functions(tree),
                'classes': CodeAnalyzer._count_classes(tree),
                'nested_loops': CodeAnalyzer._count_nested_loops(tree),
                'deepest_nesting': CodeAnalyzer._calculate_deepest_nesting(tree)
            }
            return {'success': True, 'data': complexity}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _calculate_cyclomatic_complexity(tree: ast.AST) -> int:
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or)):
                complexity += 1
            elif isinstance(node, ast.IfExp):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
        return complexity
    
    @staticmethod
    def _count_functions(tree: ast.AST) -> int:
        return sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    
    @staticmethod
    def _count_classes(tree: ast.AST) -> int:
        return sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    
    @staticmethod
    def _count_nested_loops(tree: ast.AST) -> int:
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                count += CodeAnalyzer._count_nested_children(node)
        return count
    
    @staticmethod
    def _count_nested_children(node: ast.AST) -> int:
        count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)) and child is not node:
                count += 1
        return count
    
    @staticmethod
    def _calculate_deepest_nesting(tree: ast.AST) -> int:
        max_depth = 0
        def visit(node, depth):
            nonlocal max_depth
            if isinstance(node, (ast.If, ast.For, ast.While)):
                depth += 1
                max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(node):
                visit(child, depth)
        visit(tree, 0)
        return max_depth

    @staticmethod
    def detect_errors(code: str) -> List[Dict[str, Any]]:
        errors = []
        try:
            tree = ast.parse(code)
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    if node.id not in used_names and node.id not in dir(__builtins__):
                        errors.append({
                            'type': 'undefined_variable',
                            'message': f"未定义的变量: {node.id}",
                            'line': node.lineno
                        })
            
            lines = code.splitlines()
            for i, line in enumerate(lines):
                if line.strip() and line != line.lstrip():
                    if not line.startswith(' ') and not line.startswith('\t'):
                        errors.append({
                            'type': 'indentation_error',
                            'message': f"第 {i+1} 行可能存在缩进问题",
                            'line': i+1
                        })
            
        except SyntaxError as e:
            errors.append({
                'type': 'syntax_error',
                'message': str(e),
                'line': e.lineno if hasattr(e, 'lineno') else None
            })
        
        return errors

    @staticmethod
    def format_code(code: str) -> str:
        try:
            import black
            return black.format_str(code, mode=black.FileMode())
        except ImportError:
            return code

    @staticmethod
    def run_pylint(code: str) -> List[Dict[str, Any]]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            result = subprocess.run(
                ['pylint', temp_path, '--disable=all', '--enable=warning,error'],
                capture_output=True,
                text=True
            )
            output = result.stdout + result.stderr
            issues = []
            for line in output.splitlines():
                if ':' in line and ('warning' in line.lower() or 'error' in line.lower()):
                    parts = line.split(':')
                    issues.append({
                        'type': 'warning' if 'warning' in line.lower() else 'error',
                        'message': line,
                        'line': int(parts[1]) if len(parts) > 1 else None
                    })
            return issues
        finally:
            os.unlink(temp_path)