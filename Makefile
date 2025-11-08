.PHONY: help build up down restart logs status clean lint format test shell healthcheck info

# Default target
.DEFAULT_GOAL := help

# Variables
DOCKER_COMPOSE := docker-compose
DOCKER_RUN := $(DOCKER_COMPOSE) run --rm wormhole-server
PROJECT_NAME := wormhole-server
CONTAINER_NAME := wormhole-server

help: ## Show this help message
	@echo "WormHole Server - Makefile Commands (Docker-based)"
	@echo "==================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image
	@echo "Building Docker image..."
	$(DOCKER_COMPOSE) build
	@echo "✅ Build complete!"

up: ## Start server with docker-compose
	@echo "Starting WormHole server..."
	$(DOCKER_COMPOSE) up -d
	@echo "✅ Server is running at http://localhost:8080"
	@echo "View logs: make logs"

down: ## Stop server
	@echo "Stopping WormHole server..."
	$(DOCKER_COMPOSE) down
	@echo "✅ Server stopped"

restart: ## Restart server
	@echo "Restarting WormHole server..."
	$(DOCKER_COMPOSE) restart
	@echo "✅ Server restarted"

logs: ## Show server logs (follow mode)
	$(DOCKER_COMPOSE) logs -f $(CONTAINER_NAME)

logs-tail: ## Show last 100 lines of logs
	$(DOCKER_COMPOSE) logs --tail=100 $(CONTAINER_NAME)

status: ## Check service status
	@echo "Service Status:"
	@$(DOCKER_COMPOSE) ps

clean: ## Clean up containers and cache
	@echo "Cleaning up..."
	$(DOCKER_COMPOSE) down -v --remove-orphans
	@echo "✅ Cleanup complete!"

clean-all: ## Remove containers, images, and all data
	@echo "Removing all Docker resources..."
	$(DOCKER_COMPOSE) down -v --rmi all --remove-orphans
	@echo "✅ Deep cleanup complete!"

format: ## Format code with ruff in Docker
	@echo "Formatting code with ruff..."
	@$(DOCKER_RUN) ruff check --fix .
	@$(DOCKER_RUN) ruff format .

test: ## Run tests in Docker (placeholder)
	@echo "Running tests..."
	@$(DOCKER_RUN) python -m pytest || echo "No tests configured yet"

shell: ## Open shell in running container
	@echo "Opening shell in container..."
	@docker exec -it $(CONTAINER_NAME) /bin/bash

python: ## Run Python shell in container
	@docker exec -it $(CONTAINER_NAME) python

healthcheck: ## Check server health
	@echo "Checking server health..."
	@curl -s http://localhost:8080/status | python -m json.tool 2>/dev/null || echo "❌ Server not responding. Is it running? (make up)"

info: ## Show project information
	@echo "Project: $(PROJECT_NAME)"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker Compose: $$($(DOCKER_COMPOSE) --version 2>/dev/null || echo 'Not installed')"
	@echo ""
	@echo "Container Status:"
	@$(DOCKER_COMPOSE) ps

rebuild: ## Rebuild and restart server
	@echo "Rebuilding and restarting..."
	$(DOCKER_COMPOSE) up -d --build
	@echo "✅ Server rebuilt and restarted"
