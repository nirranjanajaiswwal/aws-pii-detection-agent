# AWS Data Discovery Agent - Makefile

.PHONY: help install test clean run dashboard format lint

help: ## Show this help message
	@echo "AWS Data Discovery Agent - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and setup development environment
	python setup_dev.py

test: ## Run all tests
	python -m pytest tests/ -v

test-lf: ## Run Lake Formation integration tests
	python tests/test_lake_formation_integration.py

clean: ## Clean up temporary files and caches
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

run: ## Run the data discovery agent
	python run_agent.py

dashboard: ## Launch the Streamlit dashboard
	streamlit run servers/pii_dashboard.py

format: ## Format code with black
	black core/ servers/ tests/ --line-length 88

lint: ## Run linting with flake8
	flake8 core/ servers/ tests/ --max-line-length=88

check: ## Run all checks (format, lint, test)
	make format
	make lint
	make test

build: ## Build the package
	python -m build

dev-setup: ## Quick development setup
	pip install -e .[dev]
	pre-commit install

mcp-server: ## Start the MCP orchestrator server
	python servers/mcp_server_orchestrator.py

# AWS specific commands
aws-check: ## Check AWS configuration
	aws sts get-caller-identity
	aws s3 ls
	aws glue get-databases

# Documentation
docs: ## Generate documentation (placeholder)
	@echo "Documentation generation not implemented yet"

# Docker commands (future)
docker-build: ## Build Docker image (placeholder)
	@echo "Docker build not implemented yet"

docker-run: ## Run in Docker container (placeholder)
	@echo "Docker run not implemented yet"