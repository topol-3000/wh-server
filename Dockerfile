FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files for dependency installation
COPY pyproject.toml .

# Install dependencies using uv
# Use build arg to control dev dependencies (default: production only)
ARG IS_DEV_ENV=false
RUN if [ "$IS_DEV_ENV" = "true" ]; then \
        uv pip install --system --no-cache ".[dev]"; \
    else \
        uv pip install --system --no-cache .; \
    fi

# Copy application code
COPY src/ .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/status')" || exit 1

# Run the server
CMD ["python", "server.py"]
