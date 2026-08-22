#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Python内置的http.server模块提供静态文件服务
"""

import http.server
import socketserver
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 设置端口
PORT = 8008

# 切换到静态文件目录
os.chdir('static')

# 创建请求处理器
class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 处理根路径
        if self.path == '/':
            self.path = '/index.html'
        # 调用父类的处理方法
        super().do_GET()

# 创建服务器
with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    logger.info(f"服务器启动在 http://localhost:{PORT}")
    logger.info(f"提供静态文件服务，目录: {os.getcwd()}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务器已停止")
