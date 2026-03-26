<div align="center">
  <img src="https://img.shields.io/badge/ShieldAI-DLP-6366f1?style=for-the-badge&logo=shield&logoColor=white" alt="ShieldAI DLP" />
  <h1>ShieldAI DLP Platform</h1>
  <p><strong>Enterprise-grade Data Leakage Prevention · MLOps-powered · Startup-ready</strong></p>

  ![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
  ![Flask](https://img.shields.io/badge/Flask-2.3-lightgrey?style=flat-square)
  ![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
  ![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)
  ![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=flat-square)
</div>

---

## ✨ Features

| Category | Capability |
|---|---|
| **Scanning** | File & directory scanning · Quick/Deep/Custom modes · Real-time progress |
| **AI Detection** | Regex + ML classifier · Credit cards, SSNs, API keys, passwords & more |
| **Monitoring** | Real-time filesystem event stream |
| **Alerts** | Severity-based (critical/high/medium/low) · Acknowledge & resolve workflow |
| **Policies** | Create/edit/delete DLP policies with custom regex · Enforce alert/block/redact |
| **Reports** | Summary & detailed text reports · JSON & TXT download |
| **MLOps** | Model training pipeline · Version registry · Metrics tracking · Promote to production |
| **Auth** | Session-based login · Role-based access (admin/analyst/viewer) |
| **Database** | SQLite (dev) / PostgreSQL (prod) via SQLAlchemy |
| **Deployment** | Docker · Docker Compose · Gunicorn · Makefile |
| **CI/CD** | GitHub Actions — lint → test → Docker build |

---

## 🚀 Quick Start

### Option 1 — Docker Compose (recommended)

```bash
# 1. Copy and edit environment config
cp .env.example .env
# Edit .env: set SECRET_KEY, ADMIN_PASSWORD, etc.

# 2. Start
docker compose up -d

# 3. Open browser
open http://localhost:5000
# Default login: admin / admin  ← change on first login!
```

### Option 2 — Local Python

```bash
# 1. Create virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env → set SECRET_KEY

# 4. Run
python app.py
# or: make dev
```

---

## 🏗️ Architecture

```
shieldai-dlp/
├── app.py                  ← Flask application & all routes
├── models.py               ← SQLAlchemy ORM models
├── database.py             ← DB initialisation
├── dlp_engine.py           ← Core DLP scanning engine
├── alert_system.py         ← Email & console alert dispatch
│
├── ai_components/
│   ├── content_classifier.py   ← Regex + ML content classification
│   └── anomaly_detector.py     ← Anomaly detection model
│
├── mlops/
│   ├── pipeline.py             ← Full train → eval → register pipeline
│   ├── feature_engineering.py  ← Text feature extraction (17 features)
│   ├── model_registry.py       ← Filesystem-backed versioned model store
│   └── metrics_tracker.py      ← Lightweight experiment tracker (MLflow API)
│
├── templates/
│   ├── base.html               ← Tailwind CSS sidebar layout
│   ├── login.html
│   ├── dashboard.html          ← KPIs + Chart.js trend charts
│   ├── scanner.html            ← Scan form + live results table
│   ├── alerts.html             ← Real DB alerts + filter/ack/resolve
│   ├── policies.html           ← Policy CRUD with modal
│   ├── reports.html            ← Report history + download
│   ├── monitor.html            ← Live event stream terminal
│   ├── mlops.html              ← Training, registry, metrics charts
│   └── text_reports.html       ← Text preview + download
│
├── tests/
│   └── test_api.py             ← Flask API smoke tests (7 tests)
│
├── config/dlp_config.yaml
├── Dockerfile                  ← Multi-stage Python 3.11 build
├── docker-compose.yml
├── Makefile
├── .env.example
└── requirements.txt
```

---

## 🤖 MLOps Pipeline

The MLOps pipeline (`mlops/pipeline.py`) implements a complete ML lifecycle:

```
Data (CSV) → Feature Engineering (17 features) → RandomForest Training
    → Cross-Validation → Metrics Tracking → Model Registry → Production
```

### Train a model

```bash
# Via API (after login)
curl -X POST http://localhost:5000/api/mlops/train \
     -H "Content-Type: application/json" \
     -d '{"version": "v1.0"}'

# Or use the MLOps dashboard → "Start Training"
```

### Training data format

Place CSV files in `./data/training/`:

```csv
content,label
"SSN: 123-45-6789 found in report",1
"Hello world this is a normal document",0
"API_KEY=sk-abc123... production key",1
```

### Promote to production

```bash
curl -X POST http://localhost:5000/api/mlops/promote \
     -d '{"version":"v1.0"}'
```

---

## 🔑 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret` | Flask session key — **change in production!** |
| `DATABASE_URL` | `sqlite:///dlp.db` | SQLAlchemy connection string |
| `ADMIN_USERNAME` | `admin` | Default admin username |
| `ADMIN_PASSWORD` | `admin` | Default admin password — **change!** |
| `MAX_FILE_SIZE_MB` | `10` | Max file size for scanning |
| `DLP_SMTP_SERVER` | — | SMTP server for email alerts |
| `DLP_SMTP_PASSWORD` | — | SMTP password (env only, never in code) |

---

## 🛠️ Makefile Commands

```bash
make install      # Install Python dependencies
make dev          # Run in development mode
make prod         # Run with Gunicorn
make test         # Run pytest suite
make lint         # Run Pylint
make migrate      # Apply database migrations
make docker-build # Build Docker image
make docker-up    # Start all services
make docker-down  # Stop all services
make docker-logs  # Tail application logs
make clean        # Remove __pycache__ etc.
```

---

## 🔒 Security

- Path traversal prevention on all scan/monitor paths
- Passwords stored as bcrypt hashes (Werkzeug)
- All routes require authentication via Flask-Login
- SMTP credentials via environment variable only
- Docker container runs as non-root user (`shieldai`)
- Multi-stage Docker build minimises attack surface
- `debug=False` in production

---

## 📄 License

MIT © ShieldAI
