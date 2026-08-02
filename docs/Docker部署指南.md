# 智能化测试平台 - Docker部署指南

## 📋 概述

本文档提供了智能化测试平台的完整Docker部署方案，包括开发环境和生产环境的部署说明。

---

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少4GB可用内存
- 至少20GB可用磁盘空间

### 快速部署

#### Linux/macOS

```bash
# 1. 克隆项目
git clone <repository-url>
cd TEST

# 2. 配置环境变量
cp .env.example .env
# 编辑.env文件，配置必要的环境变量

# 3. 运行部署脚本
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

#### Windows

```bash
# 1. 克隆项目
git clone <repository-url>
cd TEST

# 2. 配置环境变量
copy .env.example .env
# 编辑.env文件，配置必要的环境变量

# 3. 运行部署脚本
cd scripts
deploy.bat
```

---

## 📦 部署文件说明

### Dockerfile

#### 后端Dockerfile（`backend/Dockerfile`）

```dockerfile
FROM python:3.11-slim
# 安装系统依赖
# 安装Python依赖
# 复制项目文件
# 收集静态文件
# 启动Gunicorn
```

**特点**：
- 使用Python 3.11官方镜像
- 多阶段构建优化镜像大小
- 使用Gunicorn作为WSGI服务器
- 支持4个worker进程

#### 前端Dockerfile（`frontend/Dockerfile`）

```dockerfile
# 构建阶段
FROM node:18-alpine as build-stage
# 安装依赖
# 构建生产版本

# 生产阶段
FROM nginx:alpine as production-stage
# 复制构建产物
# 配置Nginx
```

**特点**：
- 多阶段构建减小镜像大小
- 使用Nginx作为Web服务器
- 支持Gzip压缩
- 配置静态资源缓存

### Docker Compose

#### 生产环境（`docker-compose.yml`）

**包含的服务**：
1. **redis** - Redis缓存和消息队列
2. **postgres** - PostgreSQL数据库
3. **backend** - Django后端服务
4. **celery_worker** - Celery异步任务处理器
5. **celery_beat** - Celery定时任务调度器
6. **frontend** - Vue前端服务

**特点**：
- 使用PostgreSQL作为数据库（生产环境推荐）
- 完整的Celery支持
- 数据持久化
- 网络隔离

#### 开发环境（`docker-compose.dev.yml`）

**包含的服务**：
1. **redis** - Redis缓存和消息队列
2. **backend** - Django后端服务（开发模式）
3. **celery_worker** - Celery异步任务处理器（开发模式）
4. **frontend** - Vue前端服务

**特点**：
- 使用SQLite数据库（开发环境）
- 更快的启动速度
- 更简单的配置
- 支持热重载

### Nginx配置

#### 前端Nginx配置（`frontend/nginx.conf`）

- 前端应用路由
- API代理
- 静态资源缓存
- WebSocket支持

#### 生产Nginx配置（`nginx/nginx.conf`）

- 完整的HTTP服务器配置
- Gzip压缩
- 静态资源缓存
- 上游服务器配置
- HTTPS支持（可选）

---

## 🔧 环境配置

### 环境变量说明

创建`.env`文件，配置以下环境变量：

```bash
# Django配置
DEBUG=True                    # 开发环境设置为True，生产环境设置为False
SECRET_KEY=your-secret-key    # Django密钥，生产环境必须修改
ALLOWED_HOSTS=localhost,127.0.0.1  # 允许的主机

# 数据库配置（生产环境）
DB_ENGINE=django.db.backends.postgresql
DB_NAME=testing_platform
DB_USER=testing_user
DB_PASSWORD=testing_password
DB_HOST=postgres
DB_PORT=5432

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# Celery配置
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# 邮件配置（可选）
EMAIL_HOST=smtp.163.com
EMAIL_PORT=465
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=

# CORS配置
CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1

# AI配置（可选）
OPENAI_API_KEY=
OPENAI_API_BASE=
ANTHROPIC_API_KEY=
```

---

## 🚀 部署步骤

### 开发环境部署

#### 方式1：使用部署脚本

```bash
# Linux/macOS
./scripts/deploy.sh

# Windows
cd scripts
deploy.bat
```

#### 方式2：手动部署

```bash
# 1. 构建并启动
docker-compose -f docker-compose.dev.yml up -d --build

# 2. 查看服务状态
docker-compose -f docker-compose.dev.yml ps

# 3. 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

#### 访问服务

- 前端：http://localhost
- 后端：http://localhost:8000
- API文档：http://localhost:8000/api/schema/

### 生产环境部署

#### 方式1：使用部署脚本

```bash
# Linux/macOS
./scripts/deploy.sh

# Windows
cd scripts
deploy.bat
```

#### 方式2：手动部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑.env文件，设置DEBUG=False

# 2. 构建并启动
docker-compose up -d --build

# 3. 执行数据库迁移
docker-compose exec backend python manage.py migrate

# 4. 创建超级用户（可选）
docker-compose exec backend python manage.py createsuperuser

# 5. 查看服务状态
docker-compose ps

# 6. 查看日志
docker-compose logs -f
```

#### 访问服务

- 前端：http://localhost
- 后端：http://localhost:8000
- API文档：http://localhost:8000/api/schema/
- Django Admin：http://localhost:8000/admin/

---

## 🛠️ 常用命令

### Docker Compose命令

```bash
# 启动服务
docker-compose -f docker-compose.yml up -d

# 停止服务
docker-compose -f docker-compose.yml down

# 重启服务
docker-compose -f docker-compose.yml restart

# 查看服务状态
docker-compose -f docker-compose.yml ps

# 查看日志
docker-compose -f docker-compose.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.yml logs -f backend

# 重新构建服务
docker-compose -f docker-compose.yml build --no-cache

# 清理所有数据和容器
docker-compose -f docker-compose.yml down -v

# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh

# 执行Django命令
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
docker-compose exec backend python manage.py shell

# 查看资源使用情况
docker stats
```

### Docker命令

```bash
# 查看所有容器
docker ps -a

# 查看容器日志
docker logs <container_id>

# 进入容器
docker exec -it <container_id> bash

# 停止容器
docker stop <container_id>

# 启动容器
docker start <container_id>

# 重启容器
docker restart <container_id>

# 删除容器
docker rm <container_id>

# 查看镜像
docker images

# 删除镜像
docker rmi <image_id>

# 清理未使用的资源
docker system prune -a
```

---

## 🔍 故障排除

### 常见问题

#### 1. 容器启动失败

**问题**：容器无法启动

**解决方案**：
```bash
# 查看容器日志
docker-compose logs backend

# 检查端口是否被占用
netstat -ano | findstr :8000

# 检查环境变量配置
docker-compose config

# 重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 2. 数据库连接失败

**问题**：无法连接到数据库

**解决方案**：
```bash
# 检查PostgreSQL容器状态
docker-compose ps postgres

# 查看PostgreSQL日志
docker-compose logs postgres

# 进入PostgreSQL容器
docker-compose exec postgres psql -U testing_user -d testing_platform

# 检查数据库配置
docker-compose exec backend python manage.py dbshell
```

#### 3. Redis连接失败

**问题**：无法连接到Redis

**解决方案**：
```bash
# 检查Redis容器状态
docker-compose ps redis

# 查看Redis日志
docker-compose logs redis

# 进入Redis容器
docker-compose exec redis redis-cli

# 测试Redis连接
docker-compose exec redis redis-cli ping
```

#### 4. 前端无法访问后端

**问题**：前端页面无法调用后端API

**解决方案**：
```bash
# 检查后端服务状态
docker-compose ps backend

# 检查Nginx配置
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# 检查网络连接
docker-compose exec frontend ping backend

# 查看后端日志
docker-compose logs backend
```

#### 5. 静态文件无法加载

**问题**：静态文件404错误

**解决方案**：
```bash
# 重新收集静态文件
docker-compose exec backend python manage.py collectstatic --noinput

# 检查静态文件权限
docker-compose exec backend ls -la static/

# 检查Nginx配置
docker-compose exec frontend nginx -t
docker-compose exec frontend nginx -s reload
```

#### 6. Celery任务不执行

**问题**：Celery异步任务不执行

**解决方案**：
```bash
# 检查Celery Worker状态
docker-compose ps celery_worker

# 查看Celery Worker日志
docker-compose logs celery_worker

# 进入Celery Worker容器
docker-compose exec celery_worker celery -A backend inspect active

# 重启Celery Worker
docker-compose restart celery_worker
```

---

## 📊 监控和维护

### 日志管理

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery_worker

# 查看最近100行日志
docker-compose logs --tail=100 backend

# 导出日志到文件
docker-compose logs backend > backend.log
```

### 资源监控

```bash
# 查看容器资源使用情况
docker stats

# 查看特定容器资源使用
docker stats <container_id>

# 查看容器详细信息
docker inspect <container_id>
```

### 数据备份

```bash
# 备份PostgreSQL数据库
docker-compose exec postgres pg_dump -U testing_user testing_platform > backup.sql

# 恢复PostgreSQL数据库
docker-compose exec -T postgres psql -U testing_user testing_platform < backup.sql

# 备份媒体文件
docker run --rm -v testing_platform_backend_media:/data -v $(pwd):/backup alpine tar czf /backup/media_backup.tar.gz /data
```

### 定期清理

```bash
# 清理未使用的Docker镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune

# 清理未使用的网络
docker network prune

# 清理所有未使用的资源
docker system prune -a
```

---

## 🔒 安全建议

### 生产环境安全配置

1. **修改默认密钥**
   ```bash
   # 生成随机的SECRET_KEY
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. **使用强密码**
   - 数据库密码
   - Redis密码
   - 其他敏感信息

3. **配置HTTPS**
   - 使用SSL证书
   - 强制HTTPS跳转
   - 配置HSTS

4. **限制访问**
   - 配置防火墙
   - 限制数据库访问
   - 使用网络隔离

5. **定期更新**
   - 更新Docker镜像
   - 更新依赖包
   - 修补安全漏洞

---

## 📚 相关文档

- [SDD规范文档](../.codeartsdoer/specs/platform_upgrade/)
- [瘦身报告](./瘦身报告-最终版.md)
- [自动化配置说明](./自动化配置说明.md)
- [Docker官方文档](https://docs.docker.com/)
- [Docker Compose文档](https://docs.docker.com/compose/)

---

## 🆘 获取帮助

如有问题，请参考：
- Docker日志：`docker-compose logs`
- 项目文档：`docs/`目录
- GitHub Issues：提交问题报告

---

**文档版本**：v1.0
**更新日期**：2026-03-06
**维护人员**：CodeArts代码智能体
