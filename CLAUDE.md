# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This is a Python project using `uv` for dependency management:

```bash
# Setup virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Install pre-commit hooks
pre-commit install

# Run linting and auto-fix
ruff check --fix .

# Run type checking
pyright

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=. --cov-report=html
```

## Architecture Overview

This project processes SEC EDGAR filings with text analysis and tagging capabilities:


## Configuration

- `pyproject.toml`: Project dependencies, tool configuration (ruff, pytest, coverage)
- `pyrightconfig.json`: Type checker configuration
- Environment variables loaded from `.env` file via `python-dotenv`
- Logging level controlled by `LOG_LEVEL` environment variable


## Claude Code Instructions

Only generate comments for explaining algorithm or situation when the logic is not clear from the code.
Do **NOT** generate comments for every line of code generated.

**IMPORTANT**: When working on this project, Claude Code must ALWAYS follow these steps after making any code changes:

1. **Use pytest for test cases** do not use unittest in this project.

2. **Run Ruff linting and auto-fix** after every code modification:
   ```bash
   ruff check . --fix
   ```

3. **Check for remaining linting issues**:
   ```bash
   ruff check .
   ```

4. **Project-specific linting rules**:
   - Line length limit: **90 characters** (configured in pyproject.toml)
   - Indent width: **4 spaces**
   - Always fix simple issues like line length, imports, spacing automatically
   - Follow PEP8 standards and project conventions

5. **Type checking** (optional but recommended):
   ```bash
   pyright .
   ```

**Never skip the ruff auto-fix step** - it's configured to handle most formatting issues automatically, including line length violations, import sorting, and spacing issues.
