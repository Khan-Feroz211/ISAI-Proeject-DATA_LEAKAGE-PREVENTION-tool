FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONPATH=/app:/app/src:/app/ISAIproject

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 build-essential pkg-config libdbus-1-dev python3-dev meson ninja-build && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy only requirements first for better cache
COPY ISAIproject/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy project (don't attempt to pip-install the project root without pyproject/setup)
COPY ISAIproject /app/ISAIproject

# Copy remaining app files
COPY . /app

# ensure src package contains ai_components so `from src.ai_components...` works
COPY ISAIproject/ai_components /app/src/ai_components
RUN mkdir -p /app/src/ai_components && \
    [ -f /app/src/ai_components/__init__.py ] || touch /app/src/ai_components/__init__.py && \
    chmod -R a+rX /app/src/ai_components

# Create runtime dirs, set permissions and remove build-only packages to reduce image size
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    apt-get purge -y --auto-remove build-essential pkg-config libdbus-1-dev python3-dev meson ninja-build && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

USER appuser

EXPOSE 5000

# Use gunicorn in production (ensure 'app' exposes Flask app as `app`)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "3"]