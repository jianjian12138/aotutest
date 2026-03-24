# Docker快速开始指南

## 🚀 5分钟快速部署

### 前置条件
- ✅ 已安装Docker
- ✅ 已安装Docker Compose

### 快速部署步骤

#### 1. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件（可选，使用默认配置也可以）
```

#### 2. 启动服务

**开发环境**：
```bash
# 使用部署脚本
./scripts/deploy.sh

# 或手动执行
docker-compose -f docker-compose.dev.yml up -d
```

**生产环境**：
```bash
# 使用部署脚本
./scripts/deploy.sh

# 或手动执行
docker-compose up -d
```

#### 3. 访问服务

- 🌐 前端：http://localhost
- 🔧 后端：http://localhost:8000
- 📚 API文档：http://localhost:8000/api/schema/
- 👨‍💼 Django Admin：http://localhost:8000/admin/

---

## 📦 服务说明

### 开发环境服务

| 服务 | 端口 | 说明 |
|------|------|------|
| frontend | 80 | Vue前端应用 |
| backend | 8000 | Django后端API |
| redis | 6379 | Redis缓存和消息队列 |
| celery_worker | - | Celery异步任务处理器 |

### 生产环境服务

| 服务 | 端口 | 说明 |
|------|------|------|
| frontend | 80 | Vue前端应用 |
| backend | 8000 | Django后端API |
| redis | 6379 | Redis缓存和消息队列 |
| postgres | 5432 | PostgreSQL数据库 |
| celery_worker | - | Celery异步任务处理器 |
| celery_beat | - | Celery定时任务调度器 |

---

## 🛠️ 常用命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 重新构建
```bash
docker-compose build --no-cache
docker-compose up -d
```

### 执行Django命令
```bash
# 数据库迁移
docker-compose exec backend python manage.py migrate

# 创建超级用户
docker-compose exec backend python manage.py createsuperuser

# Django Shell
docker-compose exec backend python manage.py shell
```

---

## 🔧 故障排除

### 容器无法启动
```bash
# 查看日志
docker-compose logs backend

# 重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 端口被占用
```bash
# Windows
netstat -ano | findstr :8000

# Linux/macOS
lsof -i :8000

# 修改docker-compose.yml中的端口映射
```

### 数据库连接失败
```bash
# 检查PostgreSQL状态
docker-compose ps postgres

# 查看PostgreSQL日志
docker-compose logs postgres

# 重新创建数据库
docker-compose down -v
docker-compose up -d
```

---

## 📚 更多信息

详细部署说明请参考：[Docker部署指南](./Docker部署指南.md)

---

**更新日期**：2026-03-06
