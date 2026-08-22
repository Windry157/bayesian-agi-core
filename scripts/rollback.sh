#!/bin/bash
# =====================================================================
# Bayesian-AGI-Core 回滚脚本
# 用法: ./rollback.sh [版本号]
#   不带参数: 回滚到上一个版本
#   带版本号: 回滚到指定版本
# =====================================================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
BACKUP_DIR="/opt/bayesian-agi/backups"
SERVICE_NAME="bayesian-agi"
APP_DIR="/opt/bayesian-agi"

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

# 显示帮助
show_help() {
    echo "Bayesian-AGI-Core 回滚脚本"
    echo ""
    echo "用法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示帮助信息"
    echo "  -v, --version VERSION   回滚到指定版本"
    echo "  -l, --list              列出所有可用版本"
    echo "  -d, --dry-run           模拟回滚（不执行）"
    echo ""
    echo "示例:"
    echo "  $0                      # 回滚到上一个版本"
    echo "  $0 -v 20260115_120000  # 回滚到指定版本"
    echo "  $0 --list              # 列出所有版本"
}

# 列出所有可用版本
list_versions() {
    log_info "可用备份版本:"
    echo ""

    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "备份目录不存在: $BACKUP_DIR"
        exit 1
    fi

    # 按时间倒序列出
    versions=$(ls -lt "$BACKUP_DIR" | grep "^d" | tail -n +2)

    if [ -z "$versions" ]; then
        log_warning "没有找到任何备份版本"
        exit 0
    fi

    echo "$versions" | while read line; do
        version=$(echo "$line" | awk '{print $9}')
        date=$(echo "$line" | awk '{print $6, $7, $8}')
        size=$(echo "$line" | awk '{print $5}')

        if [ -f "$BACKUP_DIR/$version/version.txt" ]; then
            git_version=$(head -n 1 "$BACKUP_DIR/$version/version.txt" 2>/dev/null || echo "N/A")
            echo "  • $version ($date) - $size bytes - $git_version"
        else
            echo "  • $version ($date) - $size bytes"
        fi
    done
}

# 检查服务状态
check_service_status() {
    log_info "检查服务状态..."

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "服务正在运行"
        systemctl status "$SERVICE_NAME" --no-pager
    else
        log_warning "服务未运行"
    fi
}

# 执行回滚
perform_rollback() {
    local target_version=$1
    local dry_run=$2

    log_info "======================================"
    log_info "  Bayesian-AGI 回滚程序"
    log_info "======================================"
    echo ""

    # 检查权限
    if [ "$EUID" -ne 0 ]; then
        log_error "此脚本需要root权限运行"
        echo "请使用: sudo $0 $@"
        exit 1
    fi

    # 检查备份目录
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "备份目录不存在: $BACKUP_DIR"
        exit 1
    fi

    # 确定目标版本
    if [ -z "$target_version" ]; then
        log_info "未指定版本，回滚到上一个版本..."

        # 获取最新两个备份
        versions=$(ls -t "$BACKUP_DIR" 2>/dev/null | grep -v "^total" | grep -v "^d" | tail -n +2 | head -1)

        if [ -z "$versions" ]; then
            log_error "没有找到可回滚的版本"
            exit 1
        fi

        target_version=$versions
    fi

    # 检查目标版本是否存在
    if [ ! -d "$BACKUP_DIR/$target_version" ]; then
        log_error "指定版本不存在: $target_version"
        echo ""
        log_info "可用版本:"
        list_versions
        exit 1
    fi

    echo ""
    log_info "目标回滚版本: $target_version"
    echo ""

    # 显示将要恢复的文件
    log_info "将要恢复的文件:"
    ls -lh "$BACKUP_DIR/$target_version" | head -10
    echo "  ..."
    echo ""

    # 干运行模式
    if [ "$dry_run" = true ]; then
        log_warning "[干运行模式] 这不会实际执行回滚"
        echo ""
        log_info "执行以下操作:"
        echo "  1. 停止 $SERVICE_NAME 服务"
        echo "  2. 备份当前配置到临时目录"
        echo "  3. 从 $target_version 恢复文件"
        echo "  4. 重新加载配置"
        echo "  5. 启动 $SERVICE_NAME 服务"
        echo "  6. 运行健康检查"
        echo ""
        log_success "干运行完成"
        exit 0
    fi

    # 确认操作
    log_warning "此操作将回滚到版本: $target_version"
    read -p "确认继续? (y/N): " confirm

    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "操作已取消"
        exit 0
    fi

    echo ""

    # 记录当前版本
    CURRENT_VERSION=$(cat "$BACKUP_DIR/current/version.txt" 2>/dev/null || echo "unknown")
    log_info "当前版本: $CURRENT_VERSION"

    # 创建临时备份（万一需要恢复）
    TEMP_BACKUP="/tmp/bayesian-agi-pre-rollback-$(date +%Y%m%d_%H%M%S)"
    log_info "创建临时备份: $TEMP_BACKUP"
    cp -r "$APP_DIR" "$TEMP_BACKUP"

    echo ""

    # 停止服务
    log_info "[1/6] 停止服务..."
    systemctl stop "$SERVICE_NAME"
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_error "服务停止失败"
        exit 1
    fi
    log_success "服务已停止"

    echo ""

    # 恢复文件
    log_info "[2/6] 恢复文件..."
    rsync -av --exclude='*.pid' --exclude='*.log' \
        "$BACKUP_DIR/$target_version/" "$APP_DIR/"
    log_success "文件已恢复"

    echo ""

    # 设置权限
    log_info "[3/6] 设置权限..."
    chown -R bayesian:bayesian "$APP_DIR" 2>/dev/null || true
    chmod +x "$APP_DIR/scripts/"*.sh 2>/dev/null || true
    log_success "权限已设置"

    echo ""

    # 重新加载systemd
    log_info "[4/6] 重新加载systemd配置..."
    systemctl daemon-reload
    log_success "systemd配置已重新加载"

    echo ""

    # 启动服务
    log_info "[5/6] 启动服务..."
    systemctl start "$SERVICE_NAME"
    sleep 5

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "服务已启动"
    else
        log_error "服务启动失败，正在回滚..."
        systemctl start "$SERVICE_NAME"
        exit 1
    fi

    echo ""

    # 健康检查
    log_info "[6/6] 运行健康检查..."

    if curl -f -s http://localhost:8090/health > /dev/null; then
        log_success "MCP Server 健康检查通过"
    else
        log_warning "MCP Server 健康检查失败"
    fi

    echo ""

    # 显示状态
    log_success "======================================"
    log_success "  回滚完成!"
    log_success "======================================"
    echo ""
    log_info "回滚版本: $target_version"
    log_info "临时备份: $TEMP_BACKUP"
    echo ""

    # 服务状态
    echo ""
    log_info "服务状态:"
    systemctl status "$SERVICE_NAME" --no-pager | head -10
}

# 主程序
main() {
    local version=""
    local dry_run=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                version="$2"
                shift 2
                ;;
            -l|--list)
                list_versions
                exit 0
                ;;
            -d|--dry-run)
                dry_run=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done

    perform_rollback "$version" "$dry_run"
}

# 运行主程序
main "$@"
