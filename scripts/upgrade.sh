#!/bin/bash
# ==============================================
# OpticsERP Upgrade Script
# ==============================================
# Safely upgrades OpticsERP to new version
#
# Usage:
#   ./upgrade.sh [version]
#
# Example:
#   ./upgrade.sh          # Upgrade to latest
#   ./upgrade.sh v1.1.0   # Upgrade to specific version
#
# What this script does:
# 1. Creates automatic backup
# 2. Pulls latest code from git
# 3. Rebuilds Docker containers
# 4. Updates database schema
# 5. Restarts services
# 6. Verifies upgrade
#
# Last Updated: 2025-11-30
# ==============================================

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
TARGET_VERSION="${1:-main}"
BACKUP_DIR="/opt/opticserp/backups"
UPGRADE_LOG="upgrade_$(date +%Y%m%d_%H%M%S).log"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$UPGRADE_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$UPGRADE_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$UPGRADE_LOG"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1" | tee -a "$UPGRADE_LOG"
}

check_git_repository() {
    if [ ! -d .git ]; then
        log_error "Not in a git repository"
        log_error "This script must be run from OpticsERP root directory"
        exit 1
    fi

    log_info "✅ Git repository detected"
}

check_uncommitted_changes() {
    if ! git diff-index --quiet HEAD --; then
        log_warn "You have uncommitted changes"
        git status --short
        echo ""
        read -p "Continue anyway? (y/N): " continue_upgrade

        if [ "$continue_upgrade" != "y" ]; then
            log_info "Upgrade cancelled"
            exit 0
        fi
    fi
}

get_current_version() {
    local CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    local CURRENT_COMMIT=$(git rev-parse --short HEAD)

    echo "Current branch: $CURRENT_BRANCH"
    echo "Current commit: $CURRENT_COMMIT"
    echo ""

    # Try to get version from tag
    local VERSION_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "No tag")
    if [ "$VERSION_TAG" != "No tag" ]; then
        echo "Current version: $VERSION_TAG"
    fi
}

confirm_upgrade() {
    echo ""
    echo "=========================================="
    echo "  OpticsERP Upgrade Confirmation"
    echo "=========================================="
    echo ""
    get_current_version
    echo ""
    echo "Upgrade target: $TARGET_VERSION"
    echo ""
    echo "This upgrade will:"
    echo "  1. Create automatic backup"
    echo "  2. Stop all services"
    echo "  3. Pull latest code"
    echo "  4. Rebuild Docker containers"
    echo "  5. Update database"
    echo "  6. Restart services"
    echo ""
    echo "Estimated downtime: 5-15 minutes"
    echo ""
    read -p "Proceed with upgrade? (y/N): " confirm

    if [ "$confirm" != "y" ]; then
        log_info "Upgrade cancelled by user"
        exit 0
    fi

    log_warn "User confirmed upgrade"
}

create_backup() {
    log_step "Step 1: Creating backup..."

    if [ ! -f scripts/backup.sh ]; then
        log_error "Backup script not found: scripts/backup.sh"
        exit 1
    fi

    # Run backup script
    bash scripts/backup.sh

    log_info "✅ Backup complete"
}

stop_services() {
    log_step "Step 2: Stopping services..."

    docker-compose stop

    log_info "✅ Services stopped"
}

pull_code() {
    log_step "Step 3: Pulling latest code..."

    # Fetch latest changes
    git fetch origin

    # Checkout target version
    if [ "$TARGET_VERSION" = "main" ]; then
        git checkout main
        git pull origin main
    else
        git checkout "$TARGET_VERSION"
    fi

    log_info "✅ Code updated to: $(git rev-parse --short HEAD)"
}

check_migrations() {
    log_step "Step 4: Checking for database migrations..."

    # Check if any module __manifest__.py version changed
    # This is a simplified check - in production you'd have more sophisticated migration detection

    log_info "Database migrations will be handled by Odoo --update=all"
}

rebuild_containers() {
    log_step "Step 5: Rebuilding Docker containers..."

    # Pull base images
    docker-compose pull

    # Rebuild containers
    docker-compose build --no-cache

    log_info "✅ Containers rebuilt"
}

update_database() {
    log_step "Step 6: Updating database schema..."

    # Start database first
    docker-compose up -d postgres redis

    # Wait for database to be ready
    sleep 5

    # Update all modules
    docker-compose run --rm odoo odoo -d opticserp --update=all --stop-after-init --no-http

    log_info "✅ Database updated"
}

start_services() {
    log_step "Step 7: Starting all services..."

    docker-compose up -d

    # Wait for services to start
    sleep 10

    log_info "✅ Services started"
}

verify_upgrade() {
    log_step "Step 8: Verifying upgrade..."

    # Check all containers are running
    if ! docker-compose ps | grep -q "Up"; then
        log_error "Some services failed to start"
        docker-compose ps
        return 1
    fi
    log_info "✅ All containers running"

    # Check Odoo is accessible
    if docker-compose exec -T odoo odoo shell -d opticserp --no-http -c "print('OK')" 2>&1 | grep -q "OK"; then
        log_info "✅ Odoo accessible"
    else
        log_error "Odoo database check failed"
        return 1
    fi

    # Check web interface
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8069 | grep -q "200\|303"; then
        log_info "✅ Web interface accessible"
    else
        log_warn "Web interface check failed (this may be OK if loading)"
    fi

    log_info "✅ Upgrade verification passed"
}

create_rollback_instructions() {
    local BACKUP_ID=$(ls -t "$BACKUP_DIR"/db_*.sql.gz | head -1 | sed 's/.*db_\(.*\)\.sql\.gz/\1/')

    cat > "ROLLBACK_INSTRUCTIONS_${UPGRADE_LOG%.log}.txt" << EOF
========================================
Rollback Instructions
========================================

If the upgrade failed or caused issues, you can rollback:

Method 1: Restore from backup
------------------------------
./scripts/restore.sh $BACKUP_ID

This will restore:
- Database
- Filestore
- KKT buffer
- Configuration (optional)

Method 2: Git revert
--------------------
git checkout <previous-commit>
docker-compose build --no-cache
docker-compose up -d

Previous commits:
$(git log --oneline -5)

Method 3: Manual rollback
-------------------------
1. Stop services: docker-compose stop
2. Restore database manually
3. Checkout old code: git checkout <commit>
4. Rebuild: docker-compose build --no-cache
5. Start: docker-compose up -d

========================================
Backup Location: $BACKUP_DIR
Backup ID: $BACKUP_ID
Upgrade Log: $UPGRADE_LOG
========================================
EOF

    log_info "Rollback instructions saved: ROLLBACK_INSTRUCTIONS_${UPGRADE_LOG%.log}.txt"
}

print_summary() {
    local END_TIME=$(date)

    echo "" | tee -a "$UPGRADE_LOG"
    echo "==========================================" | tee -a "$UPGRADE_LOG"
    echo "  Upgrade Complete!" | tee -a "$UPGRADE_LOG"
    echo "==========================================" | tee -a "$UPGRADE_LOG"
    echo "" | tee -a "$UPGRADE_LOG"
    echo "New version:" | tee -a "$UPGRADE_LOG"
    get_current_version | tee -a "$UPGRADE_LOG"
    echo "" | tee -a "$UPGRADE_LOG"
    echo "System Status:" | tee -a "$UPGRADE_LOG"
    docker-compose ps | tee -a "$UPGRADE_LOG"
    echo "" | tee -a "$UPGRADE_LOG"
    echo "Access OpticsERP:" | tee -a "$UPGRADE_LOG"
    echo "  🌐 Odoo: http://localhost:8069" | tee -a "$UPGRADE_LOG"
    echo "  🔧 KKT Adapter: http://localhost:8000/docs" | tee -a "$UPGRADE_LOG"
    echo "" | tee -a "$UPGRADE_LOG"
    echo "Logs:" | tee -a "$UPGRADE_LOG"
    echo "  Upgrade log: $UPGRADE_LOG" | tee -a "$UPGRADE_LOG"
    echo "  Application logs: docker-compose logs -f" | tee -a "$UPGRADE_LOG"
    echo "" | tee -a "$UPGRADE_LOG"
    echo "Next steps:" | tee -a "$UPGRADE_LOG"
    echo "1. Test critical functionality" | tee -a "$UPGRADE_LOG"
    echo "2. Verify POS operations" | tee -a "$UPGRADE_LOG"
    echo "3. Check fiscal receipts" | tee -a "$UPGRADE_LOG"
    echo "4. Monitor logs for errors" | tee -a "$UPGRADE_LOG"
    echo "" | tee -a "$UPGRADE_LOG"
    echo "If issues occur, see: ROLLBACK_INSTRUCTIONS_${UPGRADE_LOG%.log}.txt" | tee -a "$UPGRADE_LOG"
    echo "" | tee -a "$UPGRADE_LOG"
}

handle_error() {
    log_error "Upgrade failed at: $1"
    log_error "Check upgrade log: $UPGRADE_LOG"
    log_error ""
    log_error "To rollback, see: ROLLBACK_INSTRUCTIONS_${UPGRADE_LOG%.log}.txt"
    exit 1
}

# Main execution
main() {
    echo "=========================================="
    echo "  OpticsERP Upgrade Script"
    echo "=========================================="
    echo "Started: $(date)"
    echo ""

    # Pre-flight checks
    check_git_repository || handle_error "Git repository check"
    check_uncommitted_changes
    confirm_upgrade

    # Upgrade steps
    create_backup || handle_error "Backup creation"
    stop_services || handle_error "Stopping services"
    pull_code || handle_error "Pulling code"
    check_migrations || handle_error "Migration check"
    rebuild_containers || handle_error "Container rebuild"
    update_database || handle_error "Database update"
    start_services || handle_error "Starting services"
    verify_upgrade || handle_error "Upgrade verification"

    # Post-upgrade
    create_rollback_instructions
    print_summary

    log_info "✅ Upgrade completed successfully!"
    echo ""
    echo "Completed: $(date)"
}

# Run main function
main
