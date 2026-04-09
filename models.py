"""
models.py – SQLAlchemy ORM models for the DLP platform.
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db


# ── Users ─────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), default="analyst")  # admin | analyst | viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


# ── Policies ──────────────────────────────────────────────────────────────────

class Policy(db.Model):
    __tablename__ = "policies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    pattern_type = db.Column(db.String(64), nullable=False)  # e.g. credit_card, ssn …
    regex_pattern = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(16), default="high")  # critical | high | medium | low
    is_active = db.Column(db.Boolean, default=True)
    action = db.Column(db.String(32), default="alert")   # alert | block | redact
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pattern_type": self.pattern_type,
            "regex_pattern": self.regex_pattern,
            "severity": self.severity,
            "is_active": self.is_active,
            "action": self.action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── Scans ─────────────────────────────────────────────────────────────────────

class ScanJob(db.Model):
    __tablename__ = "scan_jobs"

    id = db.Column(db.Integer, primary_key=True)
    target_path = db.Column(db.Text, nullable=False)
    scan_type = db.Column(db.String(32), default="quick")   # quick | deep | custom
    status = db.Column(db.String(16), default="pending")    # pending | running | done | failed
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    total_files = db.Column(db.Integer, default=0)
    sensitive_files = db.Column(db.Integer, default=0)
    failed_files = db.Column(db.Integer, default=0)
    total_bytes = db.Column(db.BigInteger, default=0)
    triggered_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    results_json = db.Column(db.Text, nullable=True)  # serialised scan output

    def to_dict(self):
        duration = None
        if self.started_at and self.finished_at:
            duration = round((self.finished_at - self.started_at).total_seconds(), 2)
        return {
            "id": self.id,
            "target_path": self.target_path,
            "scan_type": self.scan_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": duration,
            "total_files": self.total_files,
            "sensitive_files": self.sensitive_files,
            "failed_files": self.failed_files,
            "total_bytes": self.total_bytes,
        }


# ── Alerts ────────────────────────────────────────────────────────────────────

class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(16), default="medium")   # critical | high | medium | low
    alert_type = db.Column(db.String(64), default="sensitive_data")
    file_path = db.Column(db.Text, nullable=True)
    pattern_types = db.Column(db.String(512), nullable=True)  # comma-separated
    confidence = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(16), default="new")         # new | acknowledged | resolved
    scan_job_id = db.Column(db.Integer, db.ForeignKey("scan_jobs.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "type": self.alert_type,
            "file_path": self.file_path,
            "patterns": self.pattern_types.split(",") if self.pattern_types else [],
            "confidence": self.confidence,
            "status": self.status,
            "scan_job_id": self.scan_job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


# ── Reports ───────────────────────────────────────────────────────────────────

class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    report_type = db.Column(db.String(32), default="summary")  # summary | detailed | compliance
    format = db.Column(db.String(8), default="json")           # json | txt | csv
    content = db.Column(db.Text, nullable=True)
    scan_job_id = db.Column(db.Integer, db.ForeignKey("scan_jobs.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "report_type": self.report_type,
            "format": self.format,
            "scan_job_id": self.scan_job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── MLOps – Model Registry ────────────────────────────────────────────────────

class ModelVersion(db.Model):
    __tablename__ = "model_versions"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(128), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    description = db.Column(db.Text, nullable=True)
    artifact_path = db.Column(db.Text, nullable=True)
    stage = db.Column(db.String(16), default="staging")  # staging | production | archived
    accuracy = db.Column(db.Float, nullable=True)
    precision = db.Column(db.Float, nullable=True)
    recall = db.Column(db.Float, nullable=True)
    f1_score = db.Column(db.Float, nullable=True)
    training_samples = db.Column(db.Integer, nullable=True)
    parameters_json = db.Column(db.Text, nullable=True)
    trained_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "model_name": self.model_name,
            "version": self.version,
            "description": self.description,
            "artifact_path": self.artifact_path,
            "stage": self.stage,
            "metrics": {
                "accuracy": self.accuracy,
                "precision": self.precision,
                "recall": self.recall,
                "f1_score": self.f1_score,
            },
            "training_samples": self.training_samples,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
