# Testing Platform 生产环境部署指南

本文档旨在指导运维人员将 Testing Platform 从开发环境迁移并部署到生产环境。

## 1. 部署架构概览

生产环境建议采用前后端分离的部署架构：
*   **前端**: Vue 3 构建静态文件 -> Nginx 托管
*   **后端**: Django -> Gunicorn (WSGI) -> Nginx (反向代理)
*   **异步任务**: Celery Worker / Beat -> Redis (Broker)
*   **数据库**: PostgreSQL 或 MySQL (推荐 PostgreSQL 14+)
*   **缓存/消息队列**: Redis 6+

## 2. 服务器配置建议

由于平台集成了 **UI 自动化 (Playwright/Chrome)**、**AI 模型调用 (LangChain/Vanna)** 和 **性能测试 (Locust)**，对 CPU 和内存有一定要求。

### 推荐规格 (中小型团队 < 50人)

| 组件 | 推荐配置 | 说明 |
| :--- | :--- | :--- |
| **应用服务器 (App Server)** | 4核 CPU / 8GB 内存 | 运行 Django API, Celery Worker, Playwright 浏览器进程 |
| **数据库服务器 (DB Server)** | 2核 CPU / 4GB 内存 | 运行 PostgreSQL/MySQL |
| **中间件 (Redis)** | 1核 CPU / 2GB 内存 | 消息队列与缓存 |
| **存储 (Disk)** | 50GB+ SSD | 存储测试报告、截图、录像文件 |

> **注意**: 如果要在同一台机器上运行所有服务（单机部署），建议至少 **8核 CPU / 16GB 内存**，以防止 Playwright 启动多个浏览器时内存溢出。

## 3. 环境准备

### 3.1 基础软件安装
*   **OS**: Ubuntu 22.04 LTS / CentOS 7+
*   **Python**: 3.10+ (推荐 3.11)
*   **Node.js**: 16+ (用于构建前端)
*   **Nginx**: 最新稳定版
*   **PostgreSQL**: 14+ 或 **MySQL**: 8.0+
*   **Redis**: 6.0+
*   **Chrome/Webkit 依赖**: Playwright 需要系统级依赖

```bash
# Ubuntu 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nginx postgresql redis-server
# Playwright 依赖
pip install playwright
playwright install-deps
```

## 4. 数据库迁移与初始化

**核心原则**: 不要将开发环境的 SQLite 文件 (`db.sqlite3`) 直接复制到生产环境。生产环境应是一个全新的、干净的数据库。

### 步骤 1: 准备数据库
在生产环境数据库中创建库名（例如 `testing_platform`）和用户。

### 步骤 2: 修改配置
修改 `backend/settings.py` (或通过环境变量) 连接生产数据库：

```python
# settings.py 示例
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'testing_platform',
        'USER': 'prod_user',
        'PASSWORD': 'prod_password',
        'HOST': 'db_host',
        'PORT': '5432',
    }
}
```

### 步骤 3: 执行迁移
在生产环境服务器上运行以下命令，Django 会自动生成所有表结构：

```bash
cd /path/to/project
source venv/bin/activate
python manage.py migrate
```

### 步骤 4: 初始化基础数据
不要导入开发环境的测试数据。只创建必要的管理员账号和基础配置。

```bash
# 1. 创建超级管理员
python manage.py createsuperuser

# 2. (可选) 如果有基础配置数据需要导入，可以使用 loaddata
# python manage.py loaddata initial_data.json
```

## 5. 后端部署 (Django + Gunicorn)

1.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    pip install gunicorn psycopg2-binary
    ```

2.  **收集静态文件**:
    ```bash
    python manage.py collectstatic
    ```

3.  **启动 Gunicorn**:
    创建 systemd 服务文件 `/etc/systemd/system/gunicorn.service`:
    ```ini
    [Unit]
    Description=gunicorn daemon
    After=network.target

    [Service]
    User=www-data
    Group=www-data
    WorkingDirectory=/path/to/project
    ExecStart=/path/to/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/path/to/project/gunicorn.sock backend.wsgi:application

    [Install]
    WantedBy=multi-user.target
    ```

## 6. 前端部署 (Vue 3)

1.  **构建**:
    在本地或构建服务器上执行：
    ```bash
    cd frontend
    npm install
    npm run build
    ```
    这将生成 `dist` 目录。

2.  **上传**:
    将 `dist` 目录上传到生产服务器，例如 `/var/www/testing-frontend/dist`。

3.  **Nginx 配置**:
    ```nginx
    server {
        listen 80;
        server_name test-platform.example.com;

        # 前端静态文件
        location / {
            root /var/www/testing-frontend/dist;
            try_files $uri $uri/ /index.html;
        }

        # 后端 API 反向代理
        location /api/ {
            proxy_pass http://unix:/path/to/project/gunicorn.sock;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Django 管理后台
        location /admin/ {
            proxy_pass http://unix:/path/to/project/gunicorn.sock;
        }
        
        # Django 静态文件 (CSS/JS for Admin)
        location /static/ {
            alias /path/to/project/static/;
        }
        
        # 媒体文件 (测试报告/截图)
        location /media/ {
            alias /path/to/project/media/;
        }
    }
    ```

## 7. 异步任务 (Celery)

必须启动 Celery Worker 才能执行 UI 自动化和定时任务。

创建 `/etc/systemd/system/celery.service`:
```ini
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=www-data
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/celery -A backend multi start worker1 \
    --pidfile=/var/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log \
    --loglevel=INFO \
    --concurrency=4
ExecStop=/path/to/venv/bin/celery multi stopwait worker1 --pidfile=/var/run/celery/%n.pid

[Install]
WantedBy=multi-user.target
```

## 8. 总结

*   **无需手动 SQL**: Django `migrate` 会处理表结构。
*   **配置分离**: 使用 `.env` 文件或环境变量区分 `DEBUG=False` 和数据库配置。
*   **硬件重点**: 内存要足够大 (Playwright 浏览器消耗)，磁盘要定期清理 (测试报告和截图)。
