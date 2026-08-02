# 测试平台功能重构 - 部署指南

## 1. 概述

本文档提供了测试平台功能重构项目的完整部署指南，包括环境准备、配置、部署步骤、监控和维护等内容。

## 2. 系统要求

### 2.1 硬件要求

- **CPU**: 4核及以上
- **内存**: 8GB及以上
- **磁盘**: 100GB及以上
- **网络**: 稳定的网络连接

### 2.2 软件要求

- **操作系统**: Linux (推荐 Ubuntu 20.04+ 或 CentOS 7+)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.0+
- **Nginx**: 1.18+ (可选，用于手动部署)
- **Python**: 3.8+ (可选，用于本地开发)

## 3. 环境准备

### 3.1 安装 Docker

#### Ubuntu/Debian

```bash
# 更新包索引
sudo apt-get update

# 安装依赖
sudo apt-get install -y ca-certificates curl gnupg

# 添加 Docker 官方 GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 设置 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
```

#### CentOS/RHEL

```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
```

### 3.2 安装 Docker Compose

```bash
# 下载 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 添加执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 创建软链接
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# 验证安装
docker-compose --version
```

### 3.3 克隆项目

```bash
# 克隆项目
git clone <repository-url> test-platform
cd test-platform
```

## 4. 配置

### 4.1 环境变量配置

```bash
# 复制环境变量模板
cp deploy/.env.example .env

# 编辑环境变量
nano .env
```

**关键配置项说明**:

```bash
# 数据库配置
POSTGRES_DB=test_platform
POSTGRES_USER=test_user
POSTGRES_PASSWORD=your_secure_password_here  # 请修改为强密码

# Django配置
SECRET_KEY=your-secret-key-here-change-in-production  # 请修改为随机密钥
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,localhost

# CORS配置
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# 邮件配置（用于通知）
EMAIL_HOST=smtp.your-email-provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# 安全配置
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 4.2 生成随机密钥

```bash
# 生成 Django SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 4.3 SSL证书配置

#### 使用 Let's Encrypt (推荐)

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 证书会自动配置到 Nginx
```

#### 使用自签名证书（仅用于测试）

```bash
# 创建证书目录
sudo mkdir -p /etc/nginx/ssl

# 生成自签名证书
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/key.pem \
  -out /etc/nginx/ssl/cert.pem
```

### 4.4 Nginx配置

编辑 `deploy/nginx/nginx.conf`:

```nginx
# 修改域名
server_name your-domain.com www.your-domain.com;

# 修改SSL证书路径
ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
```

## 5. 部署

### 5.1 使用部署脚本（推荐）

```bash
# 进入部署目录
cd deploy

# 赋予执行权限
chmod +x deploy.sh

# 首次部署
./deploy.sh deploy
```

### 5.2 手动部署步骤

#### 步骤1: 构建镜像

```bash
cd deploy

# 构建所有服务镜像
docker-compose -f docker-compose.prod.yml build
```

#### 步骤2: 初始化数据库

```bash
# 创建数据库迁移
docker-compose -f docker-compose.prod.yml exec backend python manage.py makemigrations

# 执行数据库迁移
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

#### 步骤3: 收集静态文件

```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

#### 步骤4: 创建超级用户

```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

#### 步骤5: 启动服务

```bash
# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

#### 步骤6: 健康检查

```bash
# 检查后端API
curl http://localhost:8000/api/schema/

# 检查前端
curl http://localhost/
```

### 5.3 数据迁移

如果需要从旧系统迁移数据:

```bash
# 备份旧数据库
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_old.sql

# 执行数据迁移脚本
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate_legacy_data

# 验证数据迁移
docker-compose -f docker-compose.prod.yml exec backend python scripts/validate_migration.py
```

## 6. 访问

部署完成后，可以通过以下地址访问系统：

- **前端应用**: http://your-domain.com
- **后端API**: http://your-domain.com/api/
- **管理后台**: http://your-domain.com/admin/
- **API文档**: http://your-domain.com/api/docs/
- **Celery监控**: http://your-domain.com/flower/

## 7. 监控与维护

### 7.1 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery_worker
docker-compose -f docker-compose.prod.yml logs -f celery_beat
```

### 7.2 服务管理

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml start

# 停止服务
docker-compose -f docker-compose.prod.yml stop

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 重启特定服务
docker-compose -f docker-compose.prod.yml restart backend
```

### 7.3 数据备份

```bash
# 手动备份
./deploy.sh backup

# 或直接执行
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 7.4 数据恢复

```bash
# 恢复数据库
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB < backup_20250106_120000.sql
```

### 7.5 更新部署

```bash
# 拉取最新代码
git pull

# 更新部署
./deploy.sh update
```

### 7.6 回滚

```bash
# 查看备份列表
ls -la backups/

# 回滚到指定备份
./deploy.sh rollback backups/before_20250106_120000
```

## 8. 性能优化

### 8.1 数据库优化

```bash
# 进入数据库容器
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER $POSTGRES_DB

# 创建索引
CREATE INDEX idx_projects_project_type ON projects_project(project_type);
CREATE INDEX idx_scheduled_tasks_status ON scheduler_scheduledtask(status);
CREATE INDEX idx_reports_test_type ON reports_testreport(test_type);

# 分析查询
ANALYZE;
```

### 8.2 缓存配置

在 Django settings 中配置 Redis 缓存:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 8.3 Nginx优化

```nginx
# 在 nginx.conf 中添加
client_max_body_size 100M;
client_body_timeout 60s;
client_header_timeout 60s;
keepalive_timeout 65s;
gzip on;
gzip_comp_level 6;
gzip_types text/plain text/css application/json application/javascript;
```

## 9. 安全配置

### 9.1 防火墙配置

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 9.2 定期更新

```bash
# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 更新 Docker 镜像
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### 9.3 日志轮转

创建 `/etc/logrotate.d/test-platform`:

```
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        docker-compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload
    endscript
}
```

## 10. 故障排查

### 10.1 常见问题

#### 问题1: 服务无法启动

```bash
# 查看服务日志
docker-compose -f docker-compose.prod.yml logs

# 检查端口占用
sudo netstat -tlnp | grep -E '(:80|:443|:8000|:5432|:6379)'
```

#### 问题2: 数据库连接失败

```bash
# 检查数据库状态
docker-compose -f docker-compose.prod.yml ps postgres

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs postgres

# 测试数据库连接
docker-compose -f docker-compose.prod.yml exec postgres psql -U $POSTGRES_USER $POSTGRES_DB
```

#### 问题3: Celery任务不执行

```bash
# 查看 Celery Worker 日志
docker-compose -f docker-compose.prod.yml logs celery_worker

# 查看 Celery Beat 日志
docker-compose -f docker-compose.prod.yml logs celery_beat

# 检查 Celery 任务
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell
>>> from apps.scheduler.models import ScheduledTask
>>> ScheduledTask.objects.all()
```

#### 问题4: 前端无法访问API

```bash
# 检查 CORS 配置
# 查看 .env 文件中的 CORS_ALLOWED_ORIGINS

# 检查 Nginx 配置
docker-compose -f docker-compose.prod.yml logs nginx
```

### 10.2 日志分析

```bash
# 查看错误日志
docker-compose -f docker-compose.prod.yml logs | grep ERROR

# 查看最近的错误
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep ERROR

# 导出日志
docker-compose -f docker-compose.prod.yml logs > logs_$(date +%Y%m%d_%H%M%S).txt
```

## 11. 监控和告警

### 11.1 系统监控

使用 Prometheus + Grafana 进行系统监控:

```yaml
# 添加到 docker-compose.prod.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  volumes:
    - grafana_data:/var/lib/grafana
  ports:
    - "3000:3000"
```

### 11.2 日志监控

使用 ELK Stack (Elasticsearch, Logstash, Kibana):

```yaml
# 添加到 docker-compose.prod.yml
elasticsearch:
  image: elasticsearch:7.14.0
  environment:
    - discovery.type=single-node
  volumes:
    - es_data:/usr/share/elasticsearch/data
  ports:
    - "9200:9200"

kibana:
  image: kibana:7.14.0
  ports:
    - "5601:5601"
  depends_on:
    - elasticsearch
```

## 12. 扩展部署

### 12.1 负载均衡

使用 Nginx 进行负载均衡:

```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}
```

### 12.2 数据库主从复制

```yaml
# 添加从数据库
postgres_slave:
  image: postgres:14-alpine
  environment:
    POSTGRES_REPLICATION_MODE: slave
    POSTGRES_MASTER_SERVICE: postgres
  volumes:
    - postgres_slave_data:/var/lib/postgresql/data
```

## 13. 附录

### 13.1 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80, 443 | HTTP/HTTPS |
| Django | 8000 | 后端API |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存/消息队列 |
| Celery Flower | 5555 | 任务监控 |

### 13.2 目录结构

```
test-platform/
├── backend/              # 后端代码
├── frontend/             # 前端代码
├── deploy/               # 部署配置
│   ├── docker-compose.prod.yml
│   ├── .env.example
│   ├── nginx/
│   │   └── nginx.conf
│   └── deploy.sh
├── docs/                 # 文档
└── backups/              # 备份目录
```

### 13.3 有用的命令

```bash
# 查看Docker容器状态
docker ps

# 查看容器资源占用
docker stats

# 进入容器
docker-compose -f docker-compose.prod.yml exec backend bash

# 查看Docker磁盘使用
docker system df

# 清理未使用的Docker资源
docker system prune -a
```

---

**文档版本**: v1.0
**创建日期**: 2025-01-06
**最后更新**: 2025-01-06
