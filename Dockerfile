# 使用 Python 3.10 作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
COPY src/ src/
COPY config.yaml .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p logs memory data

# 设置环境变量
ENV PYTHONPATH=/app
ENV APP_ENV=production

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "src.main"]