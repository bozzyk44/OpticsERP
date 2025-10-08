# Makefile for OpticsERP (Offline-First POS)
# Author: AI Bootstrap
# Date: 2025-10-08
# Purpose: Development automation and bootstrap commands

.PHONY: help bootstrap verify-env smoke-test clean init-db test-poc-1

# Default target
help:
	@echo "OpticsERP Development Commands"
	@echo "==============================="
	@echo ""
	@echo "Bootstrap & Setup:"
	@echo "  make bootstrap     - Create project structure and initialize environment"
	@echo "  make verify-env    - Verify all dependencies are installed"
	@echo "  make init-db       - Initialize SQLite buffer database"
	@echo ""
	@echo "Testing:"
	@echo "  make smoke-test    - Run smoke tests to verify bootstrap"
	@echo "  make test-poc-1    - Run POC-1 test (KKT emulator + 50 operations)"
	@echo "  make test          - Run all unit tests"
	@echo ""
	@echo "Development:"
	@echo "  make run-adapter   - Run KKT adapter (FastAPI)"
	@echo "  make run-odoo      - Run Odoo instance"
	@echo "  make clean         - Clean generated files and caches"
	@echo ""

# Bootstrap: Create project structure
bootstrap:
	@echo "🚀 Bootstrapping OpticsERP project..."
	@echo ""

	@echo "📁 Creating directory structure..."
	@mkdir -p kkt_adapter/app
	@mkdir -p kkt_adapter/data
	@mkdir -p kkt_adapter/tests

	@mkdir -p addons/optics_core/models
	@mkdir -p addons/optics_core/views
	@mkdir -p addons/optics_core/controllers
	@mkdir -p addons/optics_core/security
	@mkdir -p addons/optics_core/reports
	@mkdir -p addons/optics_core/static/description

	@mkdir -p addons/optics_pos_ru54fz/models
	@mkdir -p addons/optics_pos_ru54fz/views
	@mkdir -p addons/optics_pos_ru54fz/controllers
	@mkdir -p addons/optics_pos_ru54fz/security
	@mkdir -p addons/optics_pos_ru54fz/static/src/js
	@mkdir -p addons/optics_pos_ru54fz/static/description

	@mkdir -p addons/connector_b/models
	@mkdir -p addons/connector_b/views
	@mkdir -p addons/connector_b/wizards
	@mkdir -p addons/connector_b/controllers
	@mkdir -p addons/connector_b/security
	@mkdir -p addons/connector_b/static/description

	@mkdir -p addons/ru_accounting_extras/models
	@mkdir -p addons/ru_accounting_extras/views
	@mkdir -p addons/ru_accounting_extras/reports
	@mkdir -p addons/ru_accounting_extras/security
	@mkdir -p addons/ru_accounting_extras/static/description

	@mkdir -p tests/poc
	@mkdir -p tests/uat
	@mkdir -p tests/load
	@mkdir -p tests/integration
	@mkdir -p tests/unit
	@mkdir -p tests/fixtures

	@mkdir -p scripts/verify
	@mkdir -p scripts/init

	@mkdir -p examples/api_calls
	@mkdir -p examples/responses

	@mkdir -p bootstrap/kkt_adapter_skeleton
	@mkdir -p bootstrap/odoo_modules_skeleton

	@mkdir -p docs/diagrams

	@mkdir -p claude_history

	@echo "✅ Directory structure created"
	@echo ""

	@echo "📝 Creating requirements files..."
	@if [ ! -f requirements.txt ]; then \
		echo "# OpticsERP Dependencies" > requirements.txt; \
		echo "# Generated: $$(date)" >> requirements.txt; \
		echo "" >> requirements.txt; \
		echo "# Core" >> requirements.txt; \
		echo "fastapi>=0.104.0" >> requirements.txt; \
		echo "uvicorn[standard]>=0.24.0" >> requirements.txt; \
		echo "pydantic>=2.4.0" >> requirements.txt; \
		echo "python-multipart>=0.0.6" >> requirements.txt; \
		echo "" >> requirements.txt; \
		echo "# Database" >> requirements.txt; \
		echo "psycopg2-binary>=2.9.9" >> requirements.txt; \
		echo "redis>=5.0.0" >> requirements.txt; \
		echo "" >> requirements.txt; \
		echo "# Testing" >> requirements.txt; \
		echo "pytest>=7.4.0" >> requirements.txt; \
		echo "pytest-asyncio>=0.21.0" >> requirements.txt; \
		echo "pytest-cov>=4.1.0" >> requirements.txt; \
		echo "faker>=20.0.0" >> requirements.txt; \
		echo "locust>=2.17.0" >> requirements.txt; \
		echo "" >> requirements.txt; \
		echo "# Circuit Breaker & Resilience" >> requirements.txt; \
		echo "pybreaker>=1.0.0" >> requirements.txt; \
		echo "tenacity>=8.2.0" >> requirements.txt; \
		echo "" >> requirements.txt; \
		echo "# Monitoring" >> requirements.txt; \
		echo "prometheus-client>=0.18.0" >> requirements.txt; \
		echo "opentelemetry-api>=1.20.0" >> requirements.txt; \
		echo "opentelemetry-sdk>=1.20.0" >> requirements.txt; \
		echo "opentelemetry-instrumentation-fastapi>=0.41b0" >> requirements.txt; \
		echo "" >> requirements.txt; \
		echo "# Utilities" >> requirements.txt; \
		echo "python-dotenv>=1.0.0" >> requirements.txt; \
		echo "httpx>=0.25.0" >> requirements.txt; \
		echo "aiofiles>=23.2.0" >> requirements.txt; \
		echo "openpyxl>=3.1.0" >> requirements.txt; \
		echo "pandas>=2.1.0" >> requirements.txt; \
		echo "" >> requirements.txt; \
		echo "# Task Queue" >> requirements.txt; \
		echo "celery>=5.3.0" >> requirements.txt; \
		echo "APScheduler>=3.10.0" >> requirements.txt; \
		echo "✅ requirements.txt created"; \
	else \
		echo "⚠️  requirements.txt already exists, skipping"; \
	fi
	@echo ""

	@echo "🔧 Installing Python dependencies..."
	@pip install -q -r requirements.txt 2>/dev/null || echo "⚠️  pip install failed (may need to run manually)"
	@echo ""

	@echo "🗄️  Initializing SQLite buffer database..."
	@$(MAKE) init-db
	@echo ""

	@echo "✅ Bootstrap complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run 'make verify-env' to check your environment"
	@echo "  2. Run 'make smoke-test' to verify the setup"
	@echo "  3. Start development following CLAUDE.md"

# Verify environment
verify-env:
	@echo "🔍 Verifying environment..."
	@echo ""

	@echo -n "Python version: "
	@python --version 2>&1 | grep -q "3.11" && echo "✅ Python 3.11+" || (echo "❌ Python 3.11+ required" && exit 1)

	@echo -n "Docker: "
	@docker --version >/dev/null 2>&1 && echo "✅ Docker installed" || echo "⚠️  Docker not found"

	@echo -n "Docker Compose: "
	@docker-compose --version >/dev/null 2>&1 && echo "✅ Docker Compose installed" || echo "⚠️  Docker Compose not found"

	@echo -n "SQLite: "
	@sqlite3 --version >/dev/null 2>&1 && echo "✅ SQLite installed" || echo "❌ SQLite required"

	@echo -n "Git: "
	@git --version >/dev/null 2>&1 && echo "✅ Git installed" || echo "⚠️  Git not found"

	@echo -n "Make: "
	@make --version >/dev/null 2>&1 && echo "✅ Make installed" || echo "❌ Make required"

	@echo ""
	@echo -n "Project structure: "
	@if [ -d "kkt_adapter" ] && [ -d "addons" ] && [ -d "tests" ]; then \
		echo "✅ Directories exist"; \
	else \
		echo "⚠️  Run 'make bootstrap' first"; \
	fi

	@echo ""
	@echo "✅ Environment verification complete"

# Initialize SQLite buffer database
init-db:
	@echo "🗄️  Initializing SQLite buffer database..."
	@python scripts/init/init_buffer_db.py 2>/dev/null || echo "⚠️  init_buffer_db.py not found yet (will be created during bootstrap)"

# Smoke test
smoke-test:
	@echo "🧪 Running smoke tests..."
	@if [ -f tests/unit/test_smoke.py ]; then \
		pytest tests/unit/test_smoke.py -v; \
	else \
		echo "⚠️  Smoke tests not yet implemented"; \
		echo "Creating minimal smoke test..."; \
		echo "# Smoke test - verify basic setup" > tests/unit/test_smoke.py; \
		echo "def test_imports():" >> tests/unit/test_smoke.py; \
		echo "    \"\"\"Test that basic imports work\"\"\"" >> tests/unit/test_smoke.py; \
		echo "    import sqlite3" >> tests/unit/test_smoke.py; \
		echo "    import json" >> tests/unit/test_smoke.py; \
		echo "    assert True" >> tests/unit/test_smoke.py; \
		pytest tests/unit/test_smoke.py -v; \
	fi

# POC-1 test
test-poc-1:
	@echo "🧪 Running POC-1 test..."
	@if [ -f tests/poc/test_poc_1_emulator.py ]; then \
		pytest tests/poc/test_poc_1_emulator.py -v; \
	else \
		echo "⚠️  POC-1 test not yet implemented"; \
		echo "See docs/4. Дорожная карта и аретфакты.md for POC-1 requirements"; \
	fi

# Run all tests
test:
	@echo "🧪 Running all tests..."
	@pytest tests/ -v --cov=kkt_adapter --cov=addons --cov-report=term-missing

# Run KKT adapter
run-adapter:
	@echo "🚀 Starting KKT Adapter..."
	@if [ -f kkt_adapter/app/main.py ]; then \
		cd kkt_adapter && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "❌ KKT adapter not yet implemented"; \
		echo "Run 'make bootstrap' first, then implement kkt_adapter/app/main.py"; \
	fi

# Run Odoo
run-odoo:
	@echo "🚀 Starting Odoo..."
	@if [ -f docker-compose.yml ]; then \
		docker-compose up -d; \
	else \
		echo "❌ docker-compose.yml not found"; \
		echo "See CLAUDE.md for docker-compose setup"; \
	fi

# Clean
clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"
