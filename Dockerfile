FROM python:3.12-slim-bookworm AS base

# Security Flags
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install ONLY required OS packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies early (better cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary project files
COPY app.py .
COPY dlp_engine.py .
COPY alert_system.py .
COPY config/ config/
COPY templates/ templates/
COPY static/ static/
COPY data/ data/

EXPOSE 5000

CMD ["python", "app.py"]
