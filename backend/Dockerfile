# 后端Dockerfile - Django应用
# 注意：构建上下文必须是项目根目录（docker-compose 中 context: .，dockerfile: backend/Dockerfile），
# 以保证 /app 下同时存在 manage.py、apps/ 与 backend/（settings 包），gunicorn backend.wsgi 才能正确解析。
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（位于项目根目录）
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器（UI 自动化能力依赖；--with-deps 会安装系统级依赖库）
RUN playwright install --with-deps chromium || echo "WARN: playwright browser install failed, UI tests will be unavailable"

# 复制项目文件（保留 backend/ 子目录结构）
COPY . /app

# 创建必要的目录
RUN mkdir -p logs media static allure-reports allure-results

# 注意：collectstatic 不在构建期执行——生产 settings 强制要求 SECRET_KEY 环境变量，
# 构建期没有运行时密钥。collectstatic 已放在 docker-compose 启动命令中执行。

# 以非 root 用户运行，降低容器被攻破后的影响面
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
