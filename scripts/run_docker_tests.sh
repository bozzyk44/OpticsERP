#!/bin/bash
# ==============================================
# Docker Compose Test Runner Script
# ==============================================
# Runs integration tests using Docker Compose test stack
#
# Usage:
#   ./run_docker_tests.sh [options]
#
# Options:
#   --build         Force rebuild images
#   --down          Stop services after tests
#   --keep-up       Keep services running after tests
#   --verbose       Show detailed test output
#   --filter PATTERN Run specific tests matching pattern
#
# Examples:
#   ./run_docker_tests.sh                    # Run all tests
#   ./run_docker_tests.sh --build            # Rebuild and run
#   ./run_docker_tests.sh --filter test_ofd  # Run OFD tests only
#   ./run_docker_tests.sh --keep-up          # Keep services for debugging
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
COMPOSE_FILE="docker-compose.test.yml"
TEST_TIMEOUT=300  # 5 minutes

# Parse arguments
BUILD_FLAG=""
DOWN_AFTER=true
VERBOSE_FLAG=""
TEST_FILTER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --down)
            DOWN_AFTER=true
            shift
            ;;
        --keep-up)
            DOWN_AFTER=false
            shift
            ;;
        --verbose)
            VERBOSE_FLAG="-vv"
            shift
            ;;
        --filter)
            TEST_FILTER="-k $2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--build] [--down] [--keep-up] [--verbose] [--filter PATTERN]"
            exit 1
            ;;
    esac
done

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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

cleanup() {
    if [ "$DOWN_AFTER" = true ]; then
        log_step "Stopping test services..."
        docker-compose -f "$COMPOSE_FILE" down -v
        log_info "✅ Services stopped and volumes cleaned"
    else
        log_info "Services left running (use --down to stop)"
    fi
}

# Trap errors and cleanup
trap cleanup EXIT

# Main execution
main() {
    echo "=========================================="
    echo "  Docker Compose Test Runner"
    echo "=========================================="
    echo "Started: $(date)"
    echo ""

    # Step 1: Stop existing services
    log_step "Stopping existing test services..."
    docker-compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

    # Step 2: Start services
    log_step "Starting test services..."
    if [ -n "$BUILD_FLAG" ]; then
        log_info "Building images..."
        docker-compose -f "$COMPOSE_FILE" up -d $BUILD_FLAG
    else
        docker-compose -f "$COMPOSE_FILE" up -d
    fi

    # Step 3: Wait for services ready
    log_step "Waiting for services to be ready..."

    # Wait for health checks
    local max_wait=60
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        # Check if all required services are healthy
        local healthy_count=$(docker-compose -f "$COMPOSE_FILE" ps | grep -c "(healthy)" || echo "0")

        if [ "$healthy_count" -ge 3 ]; then
            log_info "✅ All services healthy"
            break
        fi

        echo -n "."
        sleep 2
        elapsed=$((elapsed + 2))
    done

    echo ""

    if [ $elapsed -ge $max_wait ]; then
        log_error "Services failed to become healthy within ${max_wait}s"
        log_info "Showing service status:"
        docker-compose -f "$COMPOSE_FILE" ps
        exit 1
    fi

    # Step 4: Show service status
    log_info "Service status:"
    docker-compose -f "$COMPOSE_FILE" ps

    # Step 5: Run tests
    log_step "Running integration tests..."

    # Run pytest inside test_runner container
    docker-compose -f "$COMPOSE_FILE" exec -T test_runner \
        pytest tests/integration $VERBOSE_FLAG $TEST_FILTER \
        --tb=short \
        --junit-xml=/app/test-results/junit.xml \
        --html=/app/test-results/report.html \
        --self-contained-html \
        2>&1 | tee test-output.log

    local test_exit_code=${PIPESTATUS[0]}

    # Step 6: Show test results summary
    echo ""
    log_step "Test Results Summary"

    if [ $test_exit_code -eq 0 ]; then
        log_info "✅ All tests passed!"
    else
        log_error "❌ Some tests failed (exit code: $test_exit_code)"
    fi

    # Step 7: Show mock server statistics
    log_step "Mock Server Statistics"

    # OFD stats
    log_info "Mock OFD Server:"
    curl -s http://localhost:9000/ofd/v1/health | jq '.' || echo "  (unavailable)"

    # Odoo stats
    log_info "Mock Odoo Server:"
    curl -s http://localhost:8070/api/v1/health | jq '.' || echo "  (unavailable)"

    # KKT Adapter stats
    log_info "KKT Adapter:"
    curl -s http://localhost:8001/v1/kkt/buffer/status | jq '.' || echo "  (unavailable)"

    # Step 8: Show logs if tests failed
    if [ $test_exit_code -ne 0 ]; then
        log_warn "Showing last 50 lines of service logs..."
        echo ""
        echo "=== Mock OFD Logs ==="
        docker-compose -f "$COMPOSE_FILE" logs --tail=50 mock_ofd
        echo ""
        echo "=== KKT Adapter Logs ==="
        docker-compose -f "$COMPOSE_FILE" logs --tail=50 kkt_adapter
    fi

    # Return test exit code
    return $test_exit_code
}

# Run main
main
exit_code=$?

echo ""
echo "=========================================="
if [ $exit_code -eq 0 ]; then
    echo "  ✅ Test Run Successful"
else
    echo "  ❌ Test Run Failed"
fi
echo "=========================================="
echo "Completed: $(date)"
echo ""

if [ "$DOWN_AFTER" = false ]; then
    echo "Services are still running:"
    echo "  - Mock OFD:     http://localhost:9000/ofd/v1/health"
    echo "  - Mock Odoo:    http://localhost:8070/api/v1/health"
    echo "  - KKT Adapter:  http://localhost:8001/v1/health"
    echo ""
    echo "To stop services:"
    echo "  docker-compose -f $COMPOSE_FILE down -v"
fi

exit $exit_code
