#!/bin/bash
# ==============================================
# OpticsERP Backup Script
# ==============================================
# Creates complete backup of OpticsERP installation:
# - PostgreSQL database
# - Odoo filestore (attachments)
# - KKT Adapter SQLite buffer
# - Configuration files (.env, docker-compose.yml)
#
# Usage:
#   ./backup.sh [backup_dir]
#
# Default backup directory: /opt/opticserp/backups
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
BACKUP_DIR="${1:-/opt/opticserp/backups}"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="${POSTGRES_DB:-opticserp}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-90}"

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

check_docker_running() {
    if ! docker-compose ps | grep -q "Up"; then
        log_error "Docker containers are not running"
        log_error "Start with: docker-compose up -d"
        exit 1
    fi
}

create_backup_dir() {
    log_info "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"

    if [ ! -w "$BACKUP_DIR" ]; then
        log_error "Backup directory is not writable: $BACKUP_DIR"
        exit 1
    fi
}

backup_database() {
    log_info "Backing up PostgreSQL database..."

    docker-compose exec -T postgres pg_dump -U odoo "$DB_NAME" | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

    SIZE=$(du -h "$BACKUP_DIR/db_${DATE}.sql.gz" | cut -f1)
    log_info "✅ Database backup complete: $SIZE"
}

backup_filestore() {
    log_info "Backing up Odoo filestore (attachments)..."

    # Check if filestore exists
    if ! docker-compose exec -T odoo test -d "/var/lib/odoo/filestore/$DB_NAME"; then
        log_warn "Filestore directory not found, skipping"
        return 0
    fi

    docker-compose exec -T odoo tar czf - "/var/lib/odoo/filestore/$DB_NAME" > "$BACKUP_DIR/filestore_${DATE}.tar.gz"

    SIZE=$(du -h "$BACKUP_DIR/filestore_${DATE}.tar.gz" | cut -f1)
    log_info "✅ Filestore backup complete: $SIZE"
}

backup_kkt_buffer() {
    log_info "Backing up KKT Adapter SQLite buffer..."

    # Check if KKT adapter is running
    if ! docker-compose ps | grep -q "kkt_adapter.*Up"; then
        log_warn "KKT Adapter not running, skipping buffer backup"
        return 0
    fi

    # Backup SQLite database
    docker-compose exec -T kkt_adapter sh -c "sqlite3 /app/data/buffer.db '.backup /tmp/buffer.db' && cat /tmp/buffer.db" > "$BACKUP_DIR/buffer_${DATE}.db"

    SIZE=$(du -h "$BACKUP_DIR/buffer_${DATE}.db" | cut -f1)
    log_info "✅ KKT buffer backup complete: $SIZE"
}

backup_configuration() {
    log_info "Backing up configuration files..."

    # Backup .env file
    if [ -f .env ]; then
        cp .env "$BACKUP_DIR/env_${DATE}.bak"
        log_info "✅ .env backed up"
    else
        log_warn ".env file not found"
    fi

    # Backup docker-compose.yml
    if [ -f docker-compose.yml ]; then
        cp docker-compose.yml "$BACKUP_DIR/docker-compose_${DATE}.yml"
        log_info "✅ docker-compose.yml backed up"
    else
        log_warn "docker-compose.yml not found"
    fi

    # Backup kkt_adapter config
    if [ -f kkt_adapter/config.toml ]; then
        cp kkt_adapter/config.toml "$BACKUP_DIR/kkt_config_${DATE}.toml"
        log_info "✅ KKT config backed up"
    fi
}

create_backup_manifest() {
    log_info "Creating backup manifest..."

    MANIFEST="$BACKUP_DIR/manifest_${DATE}.txt"

    cat > "$MANIFEST" << EOF
OpticsERP Backup Manifest
=========================
Date: $(date)
Backup ID: $DATE
Database: $DB_NAME

Files:
------
$(ls -lh "$BACKUP_DIR"/*${DATE}* | awk '{print $9, "-", $5}')

System Info:
------------
Odoo Version: $(docker-compose exec -T odoo odoo --version 2>/dev/null || echo "Unknown")
Docker Version: $(docker --version)
Hostname: $(hostname)

To restore from this backup:
  ./scripts/restore.sh $DATE
EOF

    log_info "✅ Manifest created: $MANIFEST"
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: $RETENTION_DAYS days)..."

    # Find and delete old backups
    DELETED=0

    find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete && DELETED=$((DELETED + 1)) || true
    find "$BACKUP_DIR" -name "filestore_*.tar.gz" -mtime +$RETENTION_DAYS -delete && DELETED=$((DELETED + 1)) || true
    find "$BACKUP_DIR" -name "buffer_*.db" -mtime +$RETENTION_DAYS -delete && DELETED=$((DELETED + 1)) || true
    find "$BACKUP_DIR" -name "env_*.bak" -mtime +$RETENTION_DAYS -delete && DELETED=$((DELETED + 1)) || true
    find "$BACKUP_DIR" -name "docker-compose_*.yml" -mtime +$RETENTION_DAYS -delete && DELETED=$((DELETED + 1)) || true
    find "$BACKUP_DIR" -name "manifest_*.txt" -mtime +$RETENTION_DAYS -delete && DELETED=$((DELETED + 1)) || true

    if [ $DELETED -gt 0 ]; then
        log_info "✅ Cleaned up old backups"
    else
        log_info "No old backups to clean up"
    fi
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "  Backup Complete!"
    echo "=========================================="
    echo ""
    echo "Backup ID: $DATE"
    echo "Location: $BACKUP_DIR"
    echo ""
    echo "Files created:"
    ls -lh "$BACKUP_DIR"/*${DATE}* | awk '{print "  ", $9, "-", $5}'
    echo ""
    echo "Total backup size:"
    du -sh "$BACKUP_DIR"/*${DATE}* | awk '{sum+=$1} END {print "  ", sum}'
    echo ""
    echo "To restore from this backup:"
    echo "  ./scripts/restore.sh $DATE"
    echo ""
}

# Main execution
main() {
    echo "=========================================="
    echo "  OpticsERP Backup Script"
    echo "=========================================="
    echo "Starting backup: $(date)"
    echo ""

    check_docker_running
    create_backup_dir
    backup_database
    backup_filestore
    backup_kkt_buffer
    backup_configuration
    create_backup_manifest
    cleanup_old_backups
    print_summary

    log_info "✅ Backup completed successfully!"
}

# Run main function
main
