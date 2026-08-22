#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core 启动脚本
"""

import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description='启动 Bayesian-AGI-Core 服务')
    parser.add_argument('--port', '-p', type=int, default=8000, help='服务端口')
    parser.add_argument('--host', '-H', default='0.0.0.0', help='绑定地址')
    parser.add_argument('--reload', '-r', action='store_true', help='启用自动重载')
    parser.add_argument('--workers', '-w', type=int, default=4, help='工作进程数')
    args = parser.parse_args()
    
    # 设置环境变量
    os.environ.setdefault('OPENCLAW_MODEL_WARMUP_TIMEOUT_MS', '90000')
    
    print(f"🚀 启动 Bayesian-AGI-Core")
    print(f"📡 端口: {args.port}")
    print(f"🔄 自动重载: {'开启' if args.reload else '关闭'}")
    print(f"👥 工作进程: {args.workers}")
    print("")
    
    try:
        # 启动 uvicorn 服务
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'src.main:app',
            f'--host={args.host}',
            f'--port={args.port}',
        ]
        
        if args.reload:
            cmd.append('--reload')
        else:
            cmd.append(f'--workers={args.workers}')
        
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()