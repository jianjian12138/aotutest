#!/bin/bash

# 测试平台部署脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    log_info "依赖检查通过"
}

# 配置环境变量
setup_env() {
    log_info "配置环境变量..."

    if [ ! -f .env ]; then
        log_warn ".env 文件不存在，从 .env.example 复制..."
        cp .env.example .env

        log_warn "请编辑 .env 文件，配置必要的环境变量"
        read -p "是否现在编辑 .env 文件? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        else
            log_error "请手动编辑 .env 文件后再继续"
            exit 1
        fi
    fi

    log_info "环境变量配置完成"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."

    if [ "$1" = "before" ]; then
        BACKUP_DIR="backups/before_$(date +%Y%m%d_%H%M%S)"
    else
        BACKUP_DIR="backups/after_$(date +%Y%m%d_%H%M%S)"
    fi

    mkdir -p $BACKUP_DIR

    docker-compose exec -T postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_DIR/database.sql

    log_info "数据库备份完成: $BACKUP_DIR"
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."

    docker-compose -f docker-compose.prod.yml build

    log_info "镜像构建完成"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."

    docker-compose -f docker-compose.prod.yml exec backend python manage.py makemigrations
    docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

    log_info "数据库迁移完成"
}

# 收集静态文件
collect_static() {
    log_info "收集静态文件..."

    docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

    log_info "静态文件收集完成"
}

# 创建超级用户
create_superuser() {
    log_info "创建超级用户..."

    docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser || true

    log_info "超级用户创建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    docker-compose -f docker-compose.prod.yml up -d

    log_info "服务启动完成"
}

# 停止服务
stop_services() {
    log_info "停止服务..."

    docker-compose -f docker-compose.prod.yml down

    log_info "服务停止完成"
}

# 查看日志
view_logs() {
    docker-compose -f docker-compose.prod.yml logs -f
}

# 健康检查
health_check() {
    log_info "进行健康检查..."

    # 等待服务启动
    sleep 10

    # 检查后端API
    if curl -f http://localhost:8000/api/schema/ > /dev/null 2>&1; then
        log_info "后端API正常"
    else
        log_error "后端API异常"
        return 1
    fi

    # 检查前端
    if curl -f http://localhost/ > /dev/null 2>&1; then
        log_info "前端正常"
    else
        log_error "前端异常"
        return 1
    fi

    log_info "健康检查通过"
}

# 部署
deploy() {
    log_info "开始部署..."

    check_dependencies
    setup_env
    backup_database "before"
    build_images
    stop_services
    run_migrations
    collect_static
    start_services
    health_check
    backup_database "after"

    log_info "部署完成！"
    log_info "前端访问地址: http://localhost"
    log_info "后端API地址: http://localhost:8000/api/"
    log_info "管理后台地址: http://localhost:8000/admin/"
    log_info "Celery监控地址: http://localhost/flower/"
}

# 回滚
rollback() {
    log_warn "开始回滚..."

    BACKUP_DIR=$1

    if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
        log_error "请提供有效的备份目录"
        exit 1
    fi

    log_info "从备份恢复数据库: $BACKUP_DIR"

    docker-compose -f docker-compose.prod.yml exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB < $BACKUP_DIR/database.sql

    log_info "数据库恢复完成"
    log_info "请重启服务以应用更改"
}

# 更新
update() {
    log_info "开始更新..."

    backup_database "before"
    git pull
    build_images
    run_migrations
    collect_static
    docker-compose -f docker-compose.prod.yml up -d
    health_check
    backup_database "after"

    log_info "更新完成！"
}

# 主函数
main() {
    case "$1" in
        deploy)
            deploy
            ;;
        update)
            update
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            start_services
            ;;
        logs)
            view_logs
            ;;
        migrate)
            run_migrations
            ;;
        collectstatic)
            collect_static
            ;;
        createsuperuser)
            create_superuser
            ;;
        backup)
            backup_database "manual"
            ;;
        rollback)
            rollback $2
            ;;
        health)
            health_check
            ;;
        *)
            echo "用法: $0 {deploy|update|start|stop|restart|logs|migrate|collectstatic|createsuperuser|backup|rollback|health}"
            echo ""
            echo "命令说明:"
            echo "  deploy         - 首次部署"
            echo "  update         - 更新部署"
            echo "  start          - 启动服务"
            echo "  stop           - 停止服务"
            echo "  restart        - 重启服务"
            echo "  logs           - 查看日志"
            echo "  migrate        - 运行数据库迁移"
            echo "  collectstatic  - 收集静态文件"
            echo "  createsuperuser - 创建超级用户"
            echo "  backup         - 备份数据库"
            echo "  rollback       - 回滚到指定备份"
            echo "  health         - 健康检查"
            exit 1
            ;;
    esac
}

main "$@"
