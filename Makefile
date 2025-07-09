.PHONY: install test serve test-slack help

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests"
	@echo "  serve       - Start the server"
	@echo "  test-slack  - Test Slack integration"
	@echo "  help        - Show this help"

# Install dependencies
install:
	pip install -e .

# Run tests
test:
	cd agents && python -m pytest tests/ -v

# Start the server
serve:
	cd agents && python main.py serve

# Test Slack integration
test-slack:
	cd agents && python test_slack_integration.py

# Run with sample alert
run-sample:
	cd agents && python main.py examples/alerts/node-down.json

# Install development dependencies
install-dev:
	pip install -e ".[dev]"

# Format code
format:
	ruff format agents/

# Lint code
lint:
	ruff check agents/

# Type check
type-check:
	mypy agents/
