FROM python:3.12-slim-bookworm AS base

# Security Flags
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install ONLY required OS packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    rm -rf /var/lib/apt/lists/* && \
    # Create non-root user for security
    groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install Python dependencies early (better cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY dlp_engine.py .
COPY alert_system.py .
COPY config/ config/
COPY templates/ templates/
COPY static/ static/
COPY data/ data/

# Fix permissions and switch to non-root user
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

USER appuser

EXPOSE 5000

# Use exec form for better signal handling
CMD ["python", "app.py"]