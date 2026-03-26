.PHONY: install dev prod test lint clean docker-build docker-up docker-down migrate seed

# ── Python / Flask ─────────────────────────────────────────────────────────────
install:
pip install -r requirements.txt

dev:
FLASK_ENV=development python app.py

prod:
gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 app:app

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
flask db upgrade

seed:
python -c "from app import app, _seed_admin; _seed_admin()"

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
pylint app.py dlp_engine.py ai_components/ mlops/ models.py database.py --fail-under=7

test:
pytest tests/ -v --tb=short

# ── Docker ────────────────────────────────────────────────────────────────────
docker-build:
docker compose build

docker-up:
docker compose up -d

docker-down:
docker compose down

docker-logs:
docker compose logs -f app

docker-shell:
docker compose exec app bash

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
find . -name "*.pyc" -delete; \
rm -rf .pytest_cache reports/*.json
