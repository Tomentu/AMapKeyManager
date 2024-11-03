# 使用 Ubuntu 基础镜像
FROM ubuntu:22.04

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

# 使用阿里云源
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y \
        python3.11 \
        python3-pip \
        python3.11-dev \
        gcc \
        default-libmysqlclient-dev \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置 Python 别名（如果需要的话）
RUN if [ ! -e /usr/bin/python ]; then ln -s /usr/bin/python3.11 /usr/bin/python; fi

# 设置pip镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建非root用户
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p logs && \
    chown -R appuser:appuser logs

# 切换到非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
