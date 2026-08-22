#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HengshuAgent 安全框架移植脚本
"""

import os
import shutil
import subprocess
import sys

# 源目录（Bayesian-AGI-Core）
SOURCE_DIR = os.path.abspath("E:/laowut/Trae CN/bayesian-agi-core")

# 目标目录（HengshuAgent）
TARGET_DIR = os.path.abspath("E:/laowut/Trae CN/hengshu-agent")

# 需要移植的文件列表
FILES_TO_SYNC = [
    # 安全框架
    ("src/core/safety/security_framework.py", "src/core/safety/security_framework.py"),
    ("src/core/safety/sandbox_executor.py", "src/core/safety/sandbox_executor.py"),
    ("src/core/safety/constraint_enforcement.py", "src/core/safety/constraint_enforcement.py"),
    
    # 可观测性
    ("src/core/observability/observability_center.py", "src/core/observability/observability_center.py"),
    ("src/core/observability/tracing.py", "src/core/observability/tracing.py"),
    ("src/core/observability/metrics.py", "src/core/observability/metrics.py"),
    ("src/core/observability/rate_limiter.py", "src/core/observability/rate_limiter.py"),
    ("src/core/observability/slo_manager.py", "src/core/observability/slo_manager.py"),
    ("src/core/observability/self_healing.py", "src/core/observability/self_healing.py"),
    
    # 工具函数
    ("src/utils/__init__.py", "src/utils/__init__.py"),
    ("src/utils/singleton.py", "src/utils/singleton.py"),
    ("src/utils/logger.py", "src/utils/logger.py"),
    
    # 测试文件
    ("tests/test_security_framework.py", "tests/test_security_framework.py"),
    ("tests/test_observability.py", "tests/test_observability.py"),
]

# 需要移植的配置文件
CONFIG_FILES = [
    ("config.yaml", "config.yaml"),
    ("requirements.txt", "requirements.txt"),
]

# 需要创建的 __init__.py 文件
INIT_FILES = [
    "src/core/__init__.py",
    "src/core/safety/__init__.py",
    "src/core/observability/__init__.py",
    "src/__init__.py",
]


def create_directory(path):
    """创建目录"""
    os.makedirs(path, exist_ok=True)


def copy_file(src, dst):
    """复制文件"""
    src_path = os.path.join(SOURCE_DIR, src)
    dst_path = os.path.join(TARGET_DIR, dst)
    
    # 创建目标目录
    create_directory(os.path.dirname(dst_path))
    
    # 复制文件
    shutil.copy2(src_path, dst_path)
    print(f"✅ 复制: {src} -> {dst}")


def create_init_file(path):
    """创建 __init__.py 文件"""
    file_path = os.path.join(TARGET_DIR, path)
    
    # 检查是否已存在
    if os.path.exists(file_path):
        print(f"⚠️ 已存在: {path}")
        return
    
    # 创建目录
    create_directory(os.path.dirname(file_path))
    
    # 创建文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n")
    
    print(f"✅ 创建: {path}")


def install_dependencies():
    """安装依赖"""
    print("\n📦 安装依赖...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", os.path.join(TARGET_DIR, "requirements.txt")],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ 依赖安装成功")
    else:
        print(f"❌ 依赖安装失败: {result.stderr}")


def run_tests():
    """运行测试"""
    print("\n🧪 运行测试...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=TARGET_DIR,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.returncode == 0:
        print("✅ 所有测试通过")
    else:
        print(f"❌ 测试失败: {result.stderr}")


def main():
    """主函数"""
    print("🚀 开始移植 Bayesian-AGI-Core 到 HengshuAgent...")
    print(f"源目录: {SOURCE_DIR}")
    print(f"目标目录: {TARGET_DIR}")
    
    # 创建基础目录结构
    create_directory(TARGET_DIR)
    create_directory(os.path.join(TARGET_DIR, "src", "core", "safety"))
    create_directory(os.path.join(TARGET_DIR, "src", "core", "observability"))
    create_directory(os.path.join(TARGET_DIR, "src", "utils"))
    create_directory(os.path.join(TARGET_DIR, "tests"))
    
    # 复制核心文件
    print("\n📄 复制核心文件...")
    for src, dst in FILES_TO_SYNC:
        copy_file(src, dst)
    
    # 复制配置文件
    print("\n📋 复制配置文件...")
    for src, dst in CONFIG_FILES:
        copy_file(src, dst)
    
    # 创建 __init__.py 文件
    print("\n🔧 创建 __init__.py 文件...")
    for init_file in INIT_FILES:
        create_init_file(init_file)
    
    # 安装依赖
    install_dependencies()
    
    # 运行测试
    run_tests()
    
    print("\n🎉 移植完成！")
    print("\n📊 移植统计:")
    print(f"  - 核心文件: {len(FILES_TO_SYNC)} 个")
    print(f"  - 配置文件: {len(CONFIG_FILES)} 个")
    print(f"  - __init__.py: {len(INIT_FILES)} 个")
    print(f"  - 目标目录: {TARGET_DIR}")


if __name__ == "__main__":
    main()