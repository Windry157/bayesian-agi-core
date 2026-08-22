#!/bin/bash
# =====================================================================
# Bayesian-AGI-Core 部署脚本
# 用法: ./deploy.sh [环境] [选项]
# 环境: staging | production
# =====================================================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
SERVICE_NAME="bayesian-agi"
APP_DIR="/opt/bayesian-agi"
BACKUP_DIR="/opt/bayesian-agi/backups"
REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# 部署配置
declare -A HOSTS
HOSTS["staging"]="${STAGING_HOST:-staging.bayesian-agi.example.com}"
HOSTS["production"]="${PRODUCTION_HOST:-bayesian-agi.example.com}"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 显示帮助
show_help() {
    cat << EOF
Bayesian-AGI-Core 部署脚本

用法:
  $0 <环境> [选项]

环境:
  staging     部署到预发布环境
  production  部署到生产环境

选项:
  -h, --help              显示帮助信息
  -b, --branch <分支>     指定Git分支 (默认: 当前分支)
  -t, --tag <标签>        指定Git标签
  -s, --skip-tests        跳过测试
  -d, --skip-backup       跳过备份
  -f, --force             强制部署（不询问确认）
  -r, --rollback          部署失败时自动回滚
  --dry-run               模拟部署（不执行）

示例:
  $0 staging                        # 部署到预发布环境
  $0 production -b develop          # 从develop分支部署到生产
  $0 production -t v1.0.0        # 部署v1.0.0标签
  $0 --dry-run staging             # 模拟部署

EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    local missing_deps=()

    # 检查必要的命令
    for cmd in git curl systemctl rsync; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "缺少必要的依赖: ${missing_deps[*]}"
        exit 1
    fi

    log_success "所有依赖检查通过"
}

# 创建备份
create_backup() {
    local env=$1

    log_info "创建备份..."

    local backup_name=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$backup_name"

    mkdir -p "$backup_path"

    # 备份应用文件
    if [ -d "$APP_DIR" ]; then
        rsync -av --exclude='*.pid' --exclude='*.log' \
            --exclude='__pycache__' \
            "$APP_DIR/" "$backup_path/"

        # 保存版本信息
        echo "$CURRENT_BRANCH" > "$backup_path/branch.txt"
        echo "$CURRENT_COMMIT" > "$backup_path/commit.txt"
        echo "$(date)" > "$backup_path/deployed_at.txt"
    fi

    # 创建软链接
    rm -f "$BACKUP_DIR/current"
    ln -s "$backup_path" "$BACKUP_DIR/current"

    log_success "备份已创建: $backup_path"
    echo "$backup_path" > "$BACKUP_DIR/latest_backup.txt"
}

# 运行测试
run_tests() {
    log_info "运行测试..."

    # 单元测试
    if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
        pytest tests/ -v --tb=short || {
            log_warning "部分测试失败，继续部署..."
        }
    fi

    # 健康检查测试
    log_info "运行健康检查..."
    curl -f -s http://localhost:8090/health > /dev/null || {
        log_warning "本地健康检查失败，继续部署..."
    }

    log_success "测试完成"
}

# 拉取代码
pull_code() {
    local branch=$1

    log_info "拉取代码..."
    log_info "分支: $branch"
    log_info "提交: $CURRENT_COMMIT"

    cd "$APP_DIR"

    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        log_warning "存在未提交的更改，这些将被覆盖"
    fi

    # 拉取最新代码
    git fetch origin
    git checkout "$branch"
    git pull origin "$branch"

    log_success "代码已更新"
}

# 安装依赖
install_dependencies() {
    log_info "安装依赖..."

    cd "$APP_DIR"

    # 虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # 安装依赖
    pip install -r requirements.txt --quiet

    log_success "依赖安装完成"
}

# 重启服务
restart_service() {
    local env=$1

    log_info "重启服务..."

    # 停止服务
    log_info "停止服务..."
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    sleep 3

    # 重新加载systemd
    log_info "重新加载systemd配置..."
    systemctl daemon-reload

    # 启动服务
    log_info "启动服务..."
    systemctl start "$SERVICE_NAME"
    sleep 5

    # 检查服务状态
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "服务已启动"
    else
        log_error "服务启动失败"
        journalctl -u "$SERVICE_NAME" --no-pager -n 50
        return 1
    fi
}

# 健康检查
health_check() {
    local env=$1
    local max_attempts=10
    local attempt=1

    log_info "运行健康检查..."

    while [ $attempt -le $max_attempts ]; do
        log_info "尝试 $attempt/$max_attempts..."

        # 检查主服务
        if curl -f -s "http://localhost:8090/health" > /dev/null; then
            log_success "MCP Server 健康检查通过"

            # 检查其他端点
            curl -f -s "http://localhost:8090/tools" > /dev/null && \
                log_success "Tools端点正常"

            return 0
        fi

        sleep 3
        ((attempt++))
    done

    log_error "健康检查失败"
    return 1
}

# 发送通知
send_notification() {
    local env=$1
    local status=$2
    local message=$3

    # Slack通知（如果配置了）
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"Bayesian-AGI $env 部署 $status\",
                \"blocks\": [
                    {
                        \"type\": \"section\",
                        \"text\": {
                            \"type\": \"mrkdwn\",
                            \"text\": \"*Bayesian-AGI $env 部署 $status*\"
                        }
                    },
                    {
                        \"type\": \"context\",
                        \"elements\": [
                            {\"type\": \"mrkdwn\", \"text\": \"分支: $CURRENT_BRANCH\"},
                            {\"type\": \"mrkdwn\", \"text\": \"提交: $CURRENT_COMMIT\"}
                        ]
                    }
                ]
            }" > /dev/null
    fi
}

# 回滚
rollback_on_failure() {
    local env=$1

    log_error "部署失败，启动回滚..."

    ./scripts/rollback.sh || {
        log_error "回滚也失败了！请手动检查"
        send_notification "$env" "失败" "回滚脚本执行失败"
        exit 1
    }

    send_notification "$env" "失败并回滚" "已自动回滚到上一版本"
    log_warning "已自动回滚"
}

# 主部署流程
deploy() {
    local env=$1
    local options=${2:-""}

    local branch="$CURRENT_BRANCH"
    local skip_tests=false
    local skip_backup=false
    local force=false
    local auto_rollback=false
    local dry_run=false

    # 解析选项
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--branch)
                branch="$2"
                shift 2
                ;;
            -t|--tag)
                branch="$2"
                shift 2
                ;;
            -s|--skip-tests)
                skip_tests=true
                shift
                ;;
            -d|--skip-backup)
                skip_backup=true
                shift
                ;;
            -f|--force)
                force=true
                shift
                ;;
            -r|--rollback)
                auto_rollback=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            staging|production)
                env=$1
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    # 确认环境
    log_step "部署到 $env 环境"

    log_info "部署信息:"
    echo "  • 环境: $env"
    echo "  • 分支: $branch"
    echo "  • 提交: $CURRENT_COMMIT"
    echo "  • 跳过测试: $skip_tests"
    echo "  • 跳过备份: $skip_backup"
    echo "  • 自动回滚: $auto_rollback"
    echo ""

    # 干运行模式
    if [ "$dry_run" = true ]; then
        log_warning "[干运行模式] 这不会实际执行部署"
        echo ""
        log_info "将执行以下步骤:"
        echo "  1. 检查依赖"
        echo "  2. 创建备份"
        echo "  3. 拉取代码"
        echo "  4. 安装依赖"
        echo "  5. 重启服务"
        echo "  6. 健康检查"
        echo ""
        log_success "干运行完成"
        exit 0
    fi

    # 确认部署
    if [ "$force" != true ]; then
        read -p "确认部署? (y/N): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            log_info "部署已取消"
            exit 0
        fi
    fi

    echo ""

    # 开始部署
    trap 'rollback_on_failure $env' ERR

    log_step "[1/6] 检查环境"
    check_dependencies

    log_step "[2/6] 备份"
    if [ "$skip_backup" != true ]; then
        create_backup "$env"
    else
        log_info "跳过备份"
    fi

    log_step "[3/6] 拉取代码"
    pull_code "$branch"

    log_step "[4/6] 安装依赖"
    install_dependencies

    log_step "[5/6] 重启服务"
    restart_service "$env"

    log_step "[6/6] 健康检查"
    if health_check "$env"; then
        log_success "======================================"
        log_success "  部署成功!"
        log_success "======================================"
        send_notification "$env" "成功" "部署完成"
        exit 0
    else
        if [ "$auto_rollback" = true ]; then
            rollback_on_failure "$env"
        else
            log_error "健康检查失败，请手动检查"
            send_notification "$env" "失败" "健康检查失败"
            exit 1
        fi
    fi
}

# 主程序
main() {
    local env="staging"

    # 解析第一个参数（环境）
    case "${1:-}" in
        staging|production)
            env=$1
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
    esac

    # 执行部署
    deploy "$env" "$@"
}

# 运行主程序
main "$@"
