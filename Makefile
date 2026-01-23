.PHONY: help build up down logs restart clean backup restore shell

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
