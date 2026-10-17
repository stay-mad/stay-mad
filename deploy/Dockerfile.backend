# Multi-stage Dockerfile for Stay Mad Backend (FastAPI)
# Authority: docs/architecture/J-cloud-run-architecture.md (§53-J), docs/decisions.md (DEC-0006)

# Stage 1: Build virtual environment
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Minimal runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production

# Install runtime tools (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -g 10001 staymad && \
    useradd -u 10001 -g staymad -s /bin/sh -m staymad

# Copy virtualenv from builder
COPY --from=builder --chown=staymad:staymad /opt/venv /opt/venv

# Copy application artifacts
COPY --chown=staymad:staymad alembic.ini ./
COPY --chown=staymad:staymad backend/ /app/backend/
COPY --chown=staymad:staymad config/ /app/config/
COPY --chown=staymad:staymad docs/contracts/ /app/docs/contracts/
COPY --chown=staymad:staymad deploy/entrypoint.sh /app/deploy/entrypoint.sh

RUN chmod +x /app/deploy/entrypoint.sh

USER staymad

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
