.PHONY: help build up down logs restart clean backup restore shell test test-quick test-cov test-cov-html coverage coverage-report

help:
	@echo "FiniA Docker Commands"
	@echo "===================="
	@echo ""
	@echo "Build & Run:"
	@echo "  make build        - Build the Docker image"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make restart      - Restart services"
	@echo ""
	@echo "Testing & Coverage:"
	@echo "  make test         - Run all tests"
	@echo "  make test-quick   - Run quick tests (schema + integrity)"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make test-cov-html- Run tests with HTML coverage report"
	@echo "  make coverage     - Show coverage report"
	@echo "  make coverage-report - Open HTML coverage report"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs         - Follow API logs"
	@echo "  make shell        - Open shell in API container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean        - Remove all containers and volumes"
	@echo "  make backup       - Backup the database"
	@echo "  make restore      - Restore database from backup (set BACKUP=filename.sql)"
	@echo ""
	@echo "Examples:"
	@echo "  make up           - Start services"
	@echo "  make test-cov-html- Run tests and view coverage"
	@echo "  make logs         - Watch logs"
	@echo "  make backup BACKUP=backup_$(date +%Y%m%d).sql"

build:
	docker-compose build --no-cache

up:
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "⚠️  Please update .env with your values!"; \
		exit 1; \
	fi
	docker-compose up -d
	@echo ""
	@echo "✅ FiniA is running!"
	@echo "   🌐 Web UI: http://localhost:8000"
	@echo "   📚 API Docs: http://localhost:8000/api/docs"
	@docker-compose ps

down:
	docker-compose down

logs:
	docker-compose logs -f api

restart:
	docker-compose restart

clean:
	docker-compose down -v
	docker image prune -f
	@echo "✅ Cleanup complete!"

shell:
	docker exec -it finia-api /bin/sh

backup:
	@echo "Creating database backup..."
	docker exec finia-db mariadb-dump \
		-u$$(grep DB_USER .env | cut -d= -f2) \
		-p$$(grep DB_PASSWORD .env | cut -d= -f2) \
		$$(grep DB_NAME .env | cut -d= -f2) > finia_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup complete!"

restore:
	@if [ -z "$(BACKUP)" ]; then \
		echo "Usage: make restore BACKUP=backup.sql"; \
		exit 1; \
	fi
	@echo "Restoring from $(BACKUP)..."
	cat $(BACKUP) | docker exec -i finia-db mariadb \
		-u$$(grep DB_USER .env | cut -d= -f2) \
		-p$$(grep DB_PASSWORD .env | cut -d= -f2) \
		$$(grep DB_NAME .env | cut -d= -f2)
	@echo "✅ Restore complete!"

ps:
	docker-compose ps

status:
	@echo "Container Status:"
	@docker-compose ps
	@echo ""
	@echo "Health Checks:"
	@docker ps --format "table {{.Names}}\t{{.Status}}"

# ============================================================================
# Testing & Coverage Commands
# ============================================================================

test:
	@echo "Running all tests..."
	pytest tests/ -v

test-quick:
	@echo "Running quick tests (schema + integrity)..."
	pytest tests/integration/test_db_schema.py tests/integration/test_data_integrity.py -v

test-api:
	@echo "Running API integration tests..."
	pytest tests/integration/test_api_*.py -m api -v

test-performance:
	@echo "Running performance benchmarks..."
	pytest tests/performance/ -m performance --benchmark-only -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=term --cov-report=xml -v

test-cov-html:
	@echo "Running tests with HTML coverage report..."
	pytest tests/ \
		--cov=src \
		--cov-report=html:reports/coverage \
		--cov-report=term \
		--html=reports/test_report.html \
		--self-contained-html \
		-v
	@echo ""
	@echo "✅ Tests complete!"
	@echo "   📊 Coverage: reports/coverage/index.html"
	@echo "   📝 Test Report: reports/test_report.html"

coverage:
	@echo "Coverage Summary:"
	@pytest tests/ --cov=src --cov-report=term --quiet || true

coverage-report:
	@echo "Opening HTML coverage report..."
	@if [ -f reports/coverage/index.html ]; then \
		xdg-open reports/coverage/index.html 2>/dev/null || open reports/coverage/index.html 2>/dev/null || start reports/coverage/index.html; \
	else \
		echo "❌ Coverage report not found. Run 'make test-cov-html' first."; \
	fi

test-watch:
	@echo "Running tests in watch mode..."
	@if command -v ptw >/dev/null 2>&1; then \
		ptw -- --cov=src --cov-report=term-missing; \
	else \
		echo "❌ pytest-watch not installed. Install with: pip install pytest-watch"; \
	fi
