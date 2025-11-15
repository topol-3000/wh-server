.PHONY: help build up down restart logs clean lint format test shell

# Default target
.DEFAULT_GOAL := help

# Variables
DOCKER_COMPOSE := docker-compose -f deployments/docker-compose.dev.yml
DOCKER_RUN := $(DOCKER_COMPOSE) run --rm wormhole-server
PROJECT_NAME := wormhole-server
CONTAINER_NAME := wormhole-server
ENV_FILE := .env
ENV_EXAMPLE := .env.example

# Ensure .env file exists
.env:
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "Creating .env file from .env.example..."; \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "✅ .env file created. You can customize it if needed."; \
	fi

help: ## Show this help message
	@echo "WormHole Server - Makefile Commands (Docker-based)"
	@echo "==================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: .env ## Build Docker image
	@echo "Building Docker image..."
	$(DOCKER_COMPOSE) build
	@echo "✅ Build complete!"

up: .env ## Start server with docker-compose
	@echo "Starting WormHole server..."
	$(DOCKER_COMPOSE) up -d
	@echo "✅ Server is running"
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
	@$(DOCKER_RUN) ruff check --fix --no-cache .
	@$(DOCKER_RUN) ruff format --no-cache .

test: ## Run tests in Docker (placeholder)
	@echo "Running tests..."
	@$(DOCKER_RUN) python -m pytest || echo "No tests configured yet"

shell: ## Open shell in running container
	@echo "Opening shell in container..."
	@docker exec -it $(CONTAINER_NAME) /bin/bash

python: ## Run Python shell in container
	@docker exec -it $(CONTAINER_NAME) python

rebuild: .env ## Rebuild and restart server
	@echo "Rebuilding and restarting..."
	$(DOCKER_COMPOSE) up -d --build
	@echo "✅ Server rebuilt and restarted"
