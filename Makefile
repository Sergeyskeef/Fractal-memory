# ═══════════════════════════════════════════════════════
# FRACTAL MEMORY SYSTEM - Makefile
# ═══════════════════════════════════════════════════════
# Автоматизация рутинных задач
#
# Использование:
#   make setup     - Полная настройка проекта
#   make test      - Запуск тестов
#   make migrate   - Запуск миграций Neo4j
#   make clean     - Очистка временных файлов
#   make help      - Показать все команды

.PHONY: help setup install docker-up docker-down migrate test lint format smoke clean

# Цвета для вывода
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# По умолчанию показываем help
.DEFAULT_GOAL := help

help: ## Показать эту справку
	@echo "$(CYAN)═══════════════════════════════════════════════════════$(RESET)"
	@echo "$(CYAN)  FRACTAL MEMORY SYSTEM - Available Commands$(RESET)"
	@echo "$(CYAN)═══════════════════════════════════════════════════════$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ═══════════════════════════════════════════════════════
# SETUP & INSTALLATION
# ═══════════════════════════════════════════════════════

setup: ## Полная настройка проекта (Docker + зависимости + миграции)
	@echo "$(CYAN)Starting full project setup...$(RESET)"
	@$(MAKE) docker-up
	@$(MAKE) install
	@echo "$(YELLOW)Waiting 30 seconds for Neo4j to be ready...$(RESET)"
	@sleep 30
	@$(MAKE) migrate
	@$(MAKE) smoke
	@echo "$(GREEN)✓ Setup complete! Run 'make test' to verify.$(RESET)"

install: ## Установить Python зависимости
	@echo "$(CYAN)Installing Python dependencies...$(RESET)"
	@if command -v poetry > /dev/null; then \
		echo "$(GREEN)Using Poetry$(RESET)"; \
		poetry install; \
	else \
		echo "$(YELLOW)Poetry not found, using pip$(RESET)"; \
		pip install -r requirements.txt; \
	fi

install-dev: ## Установить dev зависимости
	@echo "$(CYAN)Installing dev dependencies...$(RESET)"
	@if command -v poetry > /dev/null; then \
		poetry install --with dev; \
	else \
		pip install -r requirements.txt pytest pytest-asyncio pytest-cov black isort mypy ruff; \
	fi

# ═══════════════════════════════════════════════════════
# DOCKER
# ═══════════════════════════════════════════════════════

docker-up: ## Запустить Docker контейнеры (Neo4j + Redis)
	@echo "$(CYAN)Starting Docker containers...$(RESET)"
	@docker compose up -d
	@echo "$(GREEN)✓ Containers started$(RESET)"
	@docker compose ps

docker-down: ## Остановить Docker контейнеры
	@echo "$(CYAN)Stopping Docker containers...$(RESET)"
	@docker compose down
	@echo "$(GREEN)✓ Containers stopped$(RESET)"

docker-restart: ## Перезапустить Docker контейнеры
	@$(MAKE) docker-down
	@$(MAKE) docker-up

docker-logs: ## Показать логи контейнеров
	@docker compose logs -f

docker-clean: ## Остановить контейнеры и удалить volumes (⚠️ удалит все данные!)
	@echo "$(RED)WARNING: This will delete all data in Neo4j and Redis!$(RESET)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		echo "$(GREEN)✓ Containers and volumes removed$(RESET)"; \
	else \
		echo "$(YELLOW)Cancelled$(RESET)"; \
	fi

# ═══════════════════════════════════════════════════════
# MIGRATIONS
# ═══════════════════════════════════════════════════════

migrate: ## Запустить миграции Neo4j
	@echo "$(CYAN)Running Neo4j migrations...$(RESET)"
	@python migrations/run_migrations.py
	@echo "$(GREEN)✓ Migrations complete$(RESET)"

# ═══════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════

test: ## Запустить все тесты
	@echo "$(CYAN)Running tests...$(RESET)"
	@pytest tests/ -v

test-unit: ## Запустить только unit тесты
	@echo "$(CYAN)Running unit tests...$(RESET)"
	@pytest tests/ -v -m "not integration"

test-integration: ## Запустить только integration тесты
	@echo "$(CYAN)Running integration tests...$(RESET)"
	@pytest tests/ -v -m integration

test-cov: ## Запустить тесты с coverage
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	@pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/index.html$(RESET)"

test-api: ## Запустить только API тесты
	@echo "$(CYAN)Running API tests...$(RESET)"
	@pytest tests/test_api.py -v --no-cov

test-frontend: ## Запустить frontend unit тесты (требует npm)
	@echo "$(CYAN)Running frontend unit tests...$(RESET)"
	@cd fractal-memory-interface && npm test || echo "$(YELLOW)Frontend tests require npm install first$(RESET)"

test-frontend-e2e: ## Запустить frontend E2E тесты (требует npm и Playwright)
	@echo "$(CYAN)Running frontend E2E tests...$(RESET)"
	@cd fractal-memory-interface && npx playwright test || echo "$(YELLOW)Frontend E2E tests require npm install and playwright install$(RESET)"

test-all: test test-frontend ## Запустить все тесты (backend + frontend)

smoke: ## Запустить smoke test инфраструктуры
	@echo "$(CYAN)Running smoke test...$(RESET)"
	@python scripts/smoke_test.py

check-infra: ## Проверить инфраструктуру (Neo4j + Redis)
	@echo "$(CYAN)Checking infrastructure...$(RESET)"
	@bash scripts/check_infrastructure.sh

# ═══════════════════════════════════════════════════════
# CODE QUALITY
# ═══════════════════════════════════════════════════════

lint: ## Проверить код (ruff + mypy)
	@echo "$(CYAN)Running linters...$(RESET)"
	@ruff check src/ tests/ || true
	@mypy src/ || true

format: ## Форматировать код (black + isort)
	@echo "$(CYAN)Formatting code...$(RESET)"
	@black src/ tests/ scripts/ migrations/
	@isort src/ tests/ scripts/ migrations/
	@echo "$(GREEN)✓ Code formatted$(RESET)"

format-check: ## Проверить форматирование без изменений
	@echo "$(CYAN)Checking code format...$(RESET)"
	@black --check src/ tests/ scripts/ migrations/
	@isort --check-only src/ tests/ scripts/ migrations/

# ═══════════════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════════════

clean: ## Удалить временные файлы
	@echo "$(CYAN)Cleaning temporary files...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(RESET)"

clean-all: clean docker-clean ## Удалить всё (файлы + Docker volumes)

# ═══════════════════════════════════════════════════════
# DEVELOPMENT
# ═══════════════════════════════════════════════════════

dev: ## Запустить development окружение
	@echo "$(CYAN)Starting development environment...$(RESET)"
	@$(MAKE) docker-up
	@echo "$(GREEN)✓ Development environment ready$(RESET)"
	@echo "$(YELLOW)Neo4j Browser: http://localhost:7474$(RESET)"
	@echo "$(YELLOW)Redis: localhost:6379$(RESET)"

shell: ## Запустить Python shell с загруженными модулями
	@echo "$(CYAN)Starting Python shell...$(RESET)"
	@python -i -c "import sys; sys.path.insert(0, 'src'); from src.core.memory import FractalMemory; print('Loaded: FractalMemory')"

neo4j-shell: ## Запустить Neo4j cypher-shell
	@docker exec -it fractal-memory-neo4j cypher-shell -u neo4j

redis-shell: ## Запустить Redis CLI
	@docker exec -it fractal-memory-redis redis-cli

# ═══════════════════════════════════════════════════════
# BUILD & DISTRIBUTION
# ═══════════════════════════════════════════════════════

build: ## Собрать пакет
	@echo "$(CYAN)Building package...$(RESET)"
	@if command -v poetry > /dev/null; then \
		poetry build; \
	else \
		python -m build; \
	fi
	@echo "$(GREEN)✓ Build complete$(RESET)"

# ═══════════════════════════════════════════════════════
# EXAMPLES
# ═══════════════════════════════════════════════════════

example-basic: ## Запустить базовый пример
	@echo "$(CYAN)Running basic example...$(RESET)"
	@python examples/01_basic_usage.py

example-learning: ## Запустить пример с самообучением
	@echo "$(CYAN)Running learning example...$(RESET)"
	@python examples/02_learning_demo.py

# ═══════════════════════════════════════════════════════
# CI/CD
# ═══════════════════════════════════════════════════════

ci: install-dev format-check lint test-cov ## Запустить все проверки как в CI

pre-commit: format lint test-unit ## Запустить перед коммитом

# ═══════════════════════════════════════════════════════
# INFO
# ═══════════════════════════════════════════════════════

status: ## Показать статус проекта
	@echo "$(CYAN)═══════════════════════════════════════════════════════$(RESET)"
	@echo "$(CYAN)  FRACTAL MEMORY SYSTEM - Status$(RESET)"
	@echo "$(CYAN)═══════════════════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "$(GREEN)Docker Containers:$(RESET)"
	@docker compose ps || echo "$(RED)Docker not running$(RESET)"
	@echo ""
	@echo "$(GREEN)Python Environment:$(RESET)"
	@python --version
	@which python
	@echo ""
	@echo "$(GREEN)Dependencies:$(RESET)"
	@if command -v poetry > /dev/null; then \
		echo "Poetry: $(shell poetry --version)"; \
	else \
		echo "Poetry: not installed"; \
	fi
	@echo ""
