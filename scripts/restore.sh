#!/bin/bash
# ==============================================
# OpticsERP Restore Script
# ==============================================
# Restores OpticsERP from backup created by backup.sh
#
# Usage:
#   ./restore.sh YYYYMMDD_HHMMSS [backup_dir]
#
# Example:
#   ./restore.sh 20251130_143000
#   ./restore.sh 20251130_143000 /mnt/backups
#
# DANGER: This will OVERWRITE current data!
#
# Last Updated: 2025-11-30
# ==============================================

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
BACKUP_DIR="${2:-/opt/opticserp/backups}"
DB_NAME="${POSTGRES_DB:-opticserp}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    echo "Usage: $0 BACKUP_ID [backup_dir]"
    echo ""
    echo "Arguments:"
    echo "  BACKUP_ID   - Backup timestamp (YYYYMMDD_HHMMSS)"
    echo "  backup_dir  - Backup directory (default: /opt/opticserp/backups)"
    echo ""
    echo "Available backups:"
    if [ -d "$BACKUP_DIR" ]; then
        ls -1 "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null | sed 's/.*db_\(.*\)\.sql\.gz/  \1/' || echo "  No backups found"
    else
        echo "  Backup directory not found: $BACKUP_DIR"
    fi
    echo ""
    echo "Example:"
    echo "  $0 20251130_143000"
    exit 1
}

check_backup_exists() {
    local DATE=$1

    log_info "Checking backup files for: $DATE"

    # Check database backup
    if [ ! -f "$BACKUP_DIR/db_${DATE}.sql.gz" ]; then
        log_error "Database backup not found: $BACKUP_DIR/db_${DATE}.sql.gz"
        return 1
    fi
    log_info "✅ Database backup found"

    # Check filestore backup (optional)
    if [ -f "$BACKUP_DIR/filestore_${DATE}.tar.gz" ]; then
        log_info "✅ Filestore backup found"
    else
        log_warn "Filestore backup not found (this is OK for fresh installations)"
    fi

    # Check buffer backup (optional)
    if [ -f "$BACKUP_DIR/buffer_${DATE}.db" ]; then
        log_info "✅ KKT buffer backup found"
    else
        log_warn "KKT buffer backup not found"
    fi

    # Check configuration backups (optional)
    if [ -f "$BACKUP_DIR/env_${DATE}.bak" ]; then
        log_info "✅ .env backup found"
    fi

    return 0
}

confirm_restore() {
    local DATE=$1

    echo ""
    echo "=========================================="
    echo "  ⚠️  WARNING: DESTRUCTIVE OPERATION"
    echo "=========================================="
    echo ""
    echo "This will restore from backup: $DATE"
    echo ""
    echo "The following will be OVERWRITTEN:"
    echo "  - PostgreSQL database ($DB_NAME)"
    echo "  - Odoo filestore (if backup exists)"
    echo "  - KKT Adapter buffer (if backup exists)"
    echo ""
    echo "Current data will be LOST!"
    echo ""
    read -p "Type 'yes' to continue, anything else to cancel: " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled by user"
        exit 0
    fi

    log_warn "User confirmed restore operation"
}

create_pre_restore_backup() {
    log_info "Creating pre-restore backup (safety measure)..."

    local PRE_RESTORE_DATE=$(date +%Y%m%d_%H%M%S)_pre_restore

    # Quick database backup
    docker-compose exec -T postgres pg_dump -U odoo "$DB_NAME" | gzip > "$BACKUP_DIR/db_${PRE_RESTORE_DATE}.sql.gz" || true

    log_info "✅ Pre-restore backup saved: db_${PRE_RESTORE_DATE}.sql.gz"
}

stop_services() {
    log_info "Stopping services..."

    docker-compose stop odoo kkt_adapter celery flower || true

    log_info "✅ Services stopped"
}

restore_database() {
    local DATE=$1

    log_info "Restoring PostgreSQL database..."

    # Drop existing connections
    docker-compose exec -T postgres psql -U odoo -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" || true

    # Drop and recreate database
    docker-compose exec -T postgres psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" || true
    docker-compose exec -T postgres psql -U odoo -d postgres -c "CREATE DATABASE $DB_NAME OWNER odoo;" || true

    # Restore from backup
    gunzip < "$BACKUP_DIR/db_${DATE}.sql.gz" | docker-compose exec -T postgres psql -U odoo -d "$DB_NAME"

    log_info "✅ Database restored"
}

restore_filestore() {
    local DATE=$1

    if [ ! -f "$BACKUP_DIR/filestore_${DATE}.tar.gz" ]; then
        log_warn "Skipping filestore restore (backup not found)"
        return 0
    fi

    log_info "Restoring Odoo filestore..."

    # Remove old filestore
    docker-compose exec -T odoo sh -c "rm -rf /var/lib/odoo/filestore/$DB_NAME" || true

    # Restore from backup
    docker-compose exec -T odoo tar xzf - -C / < "$BACKUP_DIR/filestore_${DATE}.tar.gz"

    log_info "✅ Filestore restored"
}

restore_kkt_buffer() {
    local DATE=$1

    if [ ! -f "$BACKUP_DIR/buffer_${DATE}.db" ]; then
        log_warn "Skipping KKT buffer restore (backup not found)"
        return 0
    fi

    # Check if KKT adapter is configured
    if ! docker-compose ps | grep -q "kkt_adapter"; then
        log_warn "KKT Adapter not configured, skipping buffer restore"
        return 0
    fi

    log_info "Restoring KKT Adapter SQLite buffer..."

    # Restore buffer database
    cat "$BACKUP_DIR/buffer_${DATE}.db" | docker-compose exec -T kkt_adapter sh -c "cat > /app/data/buffer.db"

    # Set permissions
    docker-compose exec -T kkt_adapter sh -c "chmod 644 /app/data/buffer.db" || true

    log_info "✅ KKT buffer restored"
}

restore_configuration() {
    local DATE=$1

    if [ ! -f "$BACKUP_DIR/env_${DATE}.bak" ]; then
        log_warn "Skipping .env restore (backup not found)"
        return 0
    fi

    log_info "Configuration files found in backup:"
    echo "  - .env (backed up as env_${DATE}.bak)"

    read -p "Restore .env file? (y/N): " restore_env

    if [ "$restore_env" = "y" ]; then
        cp .env .env.backup_$(date +%Y%m%d_%H%M%S) || true
        cp "$BACKUP_DIR/env_${DATE}.bak" .env
        log_info "✅ .env restored (old .env backed up)"
    else
        log_info "Keeping current .env file"
    fi
}

start_services() {
    log_info "Starting services..."

    docker-compose up -d

    log_info "✅ Services started"
}

verify_restore() {
    log_info "Verifying restore..."

    # Wait for services to start
    sleep 10

    # Check Odoo is accessible
    if docker-compose exec -T odoo odoo shell -d "$DB_NAME" --no-http -c "print('OK')" 2>&1 | grep -q "OK"; then
        log_info "✅ Odoo database accessible"
    else
        log_error "Odoo database check failed"
        return 1
    fi

    # Check services are running
    if docker-compose ps | grep -q "Up"; then
        log_info "✅ Services running"
    else
        log_error "Some services are not running"
        return 1
    fi

    log_info "✅ Restore verification passed"
}

print_summary() {
    local DATE=$1

    echo ""
    echo "=========================================="
    echo "  Restore Complete!"
    echo "=========================================="
    echo ""
    echo "Restored from backup: $DATE"
    echo "Location: $BACKUP_DIR"
    echo ""
    echo "Restored components:"
    echo "  ✅ PostgreSQL database"
    [ -f "$BACKUP_DIR/filestore_${DATE}.tar.gz" ] && echo "  ✅ Odoo filestore"
    [ -f "$BACKUP_DIR/buffer_${DATE}.db" ] && echo "  ✅ KKT Adapter buffer"
    echo ""
    echo "System Status:"
    docker-compose ps
    echo ""
    echo "Access OpticsERP:"
    echo "  🌐 Odoo: http://localhost:8069"
    echo "  🔧 KKT Adapter: http://localhost:8000/docs"
    echo ""
    echo "Next steps:"
    echo "1. Verify data integrity"
    echo "2. Test critical functionality"
    echo "3. Check logs for errors"
    echo ""
}

# Main execution
main() {
    # Check arguments
    if [ -z "$1" ]; then
        show_usage
    fi

    DATE=$1

    echo "=========================================="
    echo "  OpticsERP Restore Script"
    echo "=========================================="
    echo ""

    check_backup_exists "$DATE" || exit 1
    confirm_restore "$DATE"
    create_pre_restore_backup
    stop_services
    restore_database "$DATE"
    restore_filestore "$DATE"
    restore_kkt_buffer "$DATE"
    restore_configuration "$DATE"
    start_services
    verify_restore
    print_summary "$DATE"

    log_info "✅ Restore completed successfully!"
}

# Run main function
main "$@"
