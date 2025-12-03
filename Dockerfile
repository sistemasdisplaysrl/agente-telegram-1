## ===========================
##       BUILDER STAGE
## ===========================
FROM python:3.13-slim-bookworm AS builder

# Install required system packages for building wheels
# mysql client libraries needed for aiomysql
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    default-libmysqlclient-dev \
    pkg-config \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv (recommended method)
COPY --from=ghcr.io/astral-sh/uv:0.9.1 /uv /uvx /bin/

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Create venv & install dependencies using uv
RUN uv sync --frozen

# Copy application source
COPY main.py setup_webhook.py gunicorn_config.py .python-version ./

## ===========================
##      PRODUCTION STAGE
## ===========================
FROM python:3.13-slim-bookworm AS production

# Install runtime dependencies for MySQL
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
 && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy project files
COPY --from=builder /app/main.py \
                    /app/setup_webhook.py \
                    /app/gunicorn_config.py \
                    /app/.python-version \
                    /app/

# Environment configuration
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Telegram Bot
    TOKEN="" \
    BOT_USERNAME="" \
    API_URL="" \
    TOP_K="" \
    WEBHOOK_URL="" \
    PORT=8443 \
    # MySQL
    DB_HOST="" \
    DB_PORT=3306 \
    DB_USER="" \
    DB_PASSWORD="" \
    DB_NAME=""

# Expose webhook port
EXPOSE 8443

# Switch to unprivileged user
USER appuser

# Entrypoint script to setup webhook before starting gunicorn
CMD python setup_webhook.py && gunicorn -c gunicorn_config.py main:app