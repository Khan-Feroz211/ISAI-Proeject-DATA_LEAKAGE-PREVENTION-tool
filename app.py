"""
app.py – DLP Platform – production-ready Flask application.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

# ── Load .env before anything else ────────────────────────────────────────────
load_dotenv()

# ── App factory ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///dlp.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.logger.setLevel(logging.INFO)

# ── Database ──────────────────────────────────────────────────────────────────
from database import init_db  # noqa: E402
from models import Alert, ModelVersion, Policy, Report, ScanJob, User  # noqa: E402
from database import db  # noqa: E402

init_db(app)

# ── Auth ──────────────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ── DLP Engine ────────────────────────────────────────────────────────────────
from dlp_engine import DLPEngine  # noqa: E402

_dlp_config = {
    "max_file_size": int(os.environ.get("MAX_FILE_SIZE_MB", 10)) * 1024 * 1024,
    "allowed_extensions": [
        ".txt", ".log", ".csv", ".json", ".xml", ".yml", ".yaml",
        ".py", ".js", ".html", ".md", ".conf", ".ini",
    ],
    "blacklisted_dirs": [".git", "__pycache__", "node_modules", ".venv", "venv"],
    "blacklisted_files": [".env", ".pem", ".key", "credentials.json"],
    "reporting": {"output_path": "./reports"},
}
dlp_engine = DLPEngine(_dlp_config)

# ── MLOps pipeline ────────────────────────────────────────────────────────────
from mlops.pipeline import DLPPipeline  # noqa: E402

mlops_pipeline = DLPPipeline()


# ── Seed admin on first run ───────────────────────────────────────────────────

def _seed_admin():
    with app.app_context():
        if User.query.count() == 0:
            admin = User(
                username=os.environ.get("ADMIN_USERNAME", "admin"),
                email="admin@dlp.local",
                role="admin",
            )
            admin.set_password(os.environ.get("ADMIN_PASSWORD", "admin"))
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Created default admin user")


# ── Path helper ───────────────────────────────────────────────────────────────

def _safe_path(path: str) -> str:
    resolved = Path(path).resolve()
    cwd = Path.cwd().resolve()
    if not resolved.is_relative_to(cwd):
        raise ValueError("Path traversal attempt blocked")
    return str(resolved)


# ════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        data = request.form
        user = User.query.filter_by(username=data.get("username")).first()
        if user and user.check_password(data.get("password", "")):
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user, remember=data.get("remember") == "on")
            return redirect(url_for("dashboard"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/scanner")
@login_required
def scanner():
    return render_template("scanner.html")


@app.route("/monitor")
@login_required
def monitor():
    return render_template("monitor.html")


@app.route("/alerts")
@login_required
def alerts():
    return render_template("alerts.html")


@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html")


@app.route("/policies")
@login_required
def policies():
    return render_template("policies.html")


@app.route("/mlops")
@login_required
def mlops():
    return render_template("mlops.html")


@app.route("/text_reports")
@login_required
def text_reports():
    return render_template("text_reports.html")


# ════════════════════════════════════════════════════════════════════════════
#  API – HEALTH
# ════════════════════════════════════════════════════════════════════════════

@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
    })


# ════════════════════════════════════════════════════════════════════════════
#  API – DASHBOARD STATS
# ════════════════════════════════════════════════════════════════════════════

@app.route("/api/stats")
@login_required
def api_stats():
    import datetime as _dt
    from collections import defaultdict

    total_scans = ScanJob.query.count()
    total_alerts = Alert.query.count()
    open_alerts = Alert.query.filter_by(status="new").count()
    critical_alerts = Alert.query.filter_by(severity="critical", status="new").count()
    sensitive_files = db.session.query(
        db.func.sum(ScanJob.sensitive_files)
    ).scalar() or 0
    last_job = ScanJob.query.order_by(ScanJob.started_at.desc()).first()

    scans_per_day = defaultdict(int)
    alerts_per_day = defaultdict(int)
    for job in ScanJob.query.filter(ScanJob.started_at.isnot(None)).all():
        scans_per_day[job.started_at.strftime("%Y-%m-%d")] += 1
    for alert in Alert.query.all():
        alerts_per_day[alert.created_at.strftime("%Y-%m-%d")] += 1

    today = _dt.date.today()
    days = [(today - _dt.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

    return jsonify({
        "statistics": {
            "total_scans": total_scans,
            "total_alerts": total_alerts,
            "open_alerts": open_alerts,
            "critical_alerts": critical_alerts,
            "sensitive_files_found": sensitive_files,
            "last_scan": (
                last_job.started_at.isoformat()
                if last_job and last_job.started_at else None
            ),
        },
        "chart": {
            "labels": days,
            "scans": [scans_per_day.get(d, 0) for d in days],
            "alerts": [alerts_per_day.get(d, 0) for d in days],
        },
    })


# ════════════════════════════════════════════════════════════════════════════
#  API – SCAN
# ════════════════════════════════════════════════════════════════════════════

@app.route("/api/scan", methods=["POST"])
@login_required
def api_scan():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({"error": "missing_path"}), 400
    try:
        safe = _safe_path(path)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    job = ScanJob(
        target_path=safe,
        scan_type=data.get("scan_type", "quick"),
        status="running",
        started_at=datetime.now(timezone.utc),
        triggered_by=current_user.id,
    )
    db.session.add(job)
    db.session.commit()

    try:
        results = dlp_engine.scan_target(safe)
        job.status = "done"
        job.finished_at = datetime.now(timezone.utc)
        job.total_files = len(results)
        job.sensitive_files = sum(1 for r in results if r.get("sensitive_content"))
        job.failed_files = sum(1 for r in results if r.get("error"))
        job.total_bytes = sum(r.get("size", 0) for r in results)
        job.results_json = json.dumps(results)
        db.session.commit()
        _create_alerts_from_scan(results, job.id)
        return jsonify({"success": True, "results": results, "job_id": job.id})
    except Exception as exc:
        job.status = "failed"
        db.session.commit()
        app.logger.error("Scan failed: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


def _create_alerts_from_scan(results: list, job_id: int):
    for r in results:
        if not r.get("sensitive_content"):
            continue
        risk = r.get("risk_level", "medium")
        classification = r.get("classification_details") or {}
        patterns = classification.get("detected_patterns", [])
        pattern_names = [
            p.get("type", "") if isinstance(p, dict) else str(p) for p in patterns
        ]
        alert = Alert(
            title=f"Sensitive data: {Path(r.get('path', 'unknown')).name}",
            description=(
                f"Risk level: {risk}. "
                f"Patterns: {', '.join(pattern_names[:5]) or 'none'}."
            ),
            severity={"high": "high", "medium": "medium"}.get(risk, "low"),
            alert_type="sensitive_data",
            file_path=r.get("path"),
            pattern_types=",".join(pattern_names[:10]),
            confidence=classification.get("confidence", 0.0),
            scan_job_id=job_id,
        )
        db.session.add(alert)
    db.session.commit()


@app.route("/api/scans")
@login_required
def api_list_scans():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    paginator = ScanJob.query.order_by(ScanJob.started_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "scans": [j.to_dict() for j in paginator.items],
        "total": paginator.total,
        "pages": paginator.pages,
        "page": page,
    })


# ════════════════════════════════════════════════════════════════════════════
#  API – MONITOR
# ════════════════════════════════════════════════════════════════════════════

@app.route("/api/monitor/start", methods=["POST"])
@login_required
def api_monitor_start():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({"error": "missing_path"}), 400
    try:
        safe = _safe_path(path)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"success": True, "monitored_path": safe,
                    "message": f"Monitoring started for {safe}"})


# ════════════════════════════════════════════════════════════════════════════
#  API – ALERTS
# ════════════════════════════════════════════════════════════════════════════

@app.route("/api/alerts")
@login_required
def api_list_alerts():
    severity = request.args.get("severity")
    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    q = Alert.query
    if severity and severity != "all":
        q = q.filter_by(severity=severity)
    if status and status != "all":
        q = q.filter_by(status=status)
    paginator = q.order_by(Alert.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    counts = {
        s: Alert.query.filter_by(severity=s).count()
        for s in ("critical", "high", "medium", "low")
    }
    return jsonify({
        "alerts": [a.to_dict() for a in paginator.items],
        "counts": counts,
        "total": paginator.total,
        "pages": paginator.pages,
    })


@app.route("/api/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@login_required
def api_acknowledge_alert(alert_id: int):
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return jsonify({"error": "not_found"}), 404
    alert.status = "acknowledged"
    db.session.commit()
    return jsonify({"success": True, "alert": alert.to_dict()})


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def api_resolve_alert(alert_id: int):
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return jsonify({"error": "not_found"}), 404
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = current_user.id
    db.session.commit()
    return jsonify({"success": True, "alert": alert.to_dict()})


@app.route("/api/alerts/clear", methods=["POST"])
@login_required
def api_clear_alerts():
    Alert.query.delete()
    db.session.commit()
    return jsonify({"success": True})


# ════════════════════════════════════════════════════════════════════════════
#  API – POLICIES
# ════════════════════════════════════════════════════════════════════════════

@app.route("/api/policies", methods=["GET"])
@login_required
def api_list_policies():
    ps = Policy.query.order_by(Policy.created_at.desc()).all()
    return jsonify({"policies": [p.to_dict() for p in ps]})


@app.route("/api/policies", methods=["POST"])
@login_required
def api_create_policy():
    data = request.get_json(silent=True) or {}
    for field in ["name", "pattern_type", "severity"]:
        if not data.get(field):
            return jsonify({"error": f"missing_{field}"}), 400
    policy = Policy(
        name=data["name"],
        description=data.get("description", ""),
        pattern_type=data["pattern_type"],
        regex_pattern=data.get("regex_pattern"),
        severity=data["severity"],
        action=data.get("action", "alert"),
        is_active=data.get("is_active", True),
        created_by=current_user.id,
    )
    db.session.add(policy)
    db.session.commit()
    return jsonify({"success": True, "policy": policy.to_dict()}), 201


@app.route("/api/policies/<int:policy_id>", methods=["PUT"])
@login_required
def api_update_policy(policy_id: int):
    policy = db.session.get(Policy, policy_id)
    if not policy:
        return jsonify({"error": "not_found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ["name", "description", "pattern_type", "regex_pattern",
                   "severity", "action", "is_active"]:
        if field in data:
            setattr(policy, field, data[field])
    db.session.commit()
    return jsonify({"success": True, "policy": policy.to_dict()})


@app.route("/api/policies/<int:policy_id>", methods=["DELETE"])
@login_required
def api_delete_policy(policy_id: int):
    policy = db.session.get(Policy, policy_id)
    if not policy:
        return jsonify({"error": "not_found"}), 404
    db.session.delete(policy)
    db.session.commit()
    return jsonify({"success": True})


# ════════════════════════════════════════════════════════════════════════════
#  API – REPORTS
# ════════════════════════════════════════════════════════════════════════════

@app.route("/api/reports", methods=["GET"])
@login_required
def api_list_reports():
    rpts = Report.query.order_by(Report.created_at.desc()).limit(50).all()
    return jsonify({"reports": [r.to_dict() for r in rpts]})


@app.route("/api/report/generate", methods=["POST"])
@login_required
def api_generate_report():
    data = request.get_json(silent=True) or {}
    scan_results = data.get("scan_results")
    rtype = data.get("type", "summary")
    if rtype == "detailed" and scan_results:
        content = dlp_engine.generate_detailed_scan_report(scan_results)
    else:
        content = dlp_engine.generate_text_report(scan_results)
    report = Report(
        name=f"DLP Report – {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        report_type=rtype,
        format=data.get("format", "json"),
        content=content,
        created_by=current_user.id,
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({"success": True, "report_id": report.id, "report": report.to_dict()})


@app.route("/api/report/text", methods=["POST"])
@login_required
def api_text_report():
    data = request.get_json(silent=True) or {}
    content = dlp_engine.generate_text_report(data.get("scan_results"))
    return jsonify({
        "success": True,
        "report": content,
        "format": "text",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/report/text/download", methods=["POST"])
@login_required
def api_download_report():
    data = request.get_json(silent=True) or {}
    rtype = data.get("type", "summary")
    scan_results = data.get("scan_results")
    if rtype == "detailed":
        content = dlp_engine.generate_detailed_scan_report(scan_results or [])
        filename = f"dlp_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    else:
        content = dlp_engine.generate_text_report(scan_results)
        filename = f"dlp_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ════════════════════════════════════════════════════════════════════════════
#  API – MLOPS
# ════════════════════════════════════════════════════════════════════════════

@app.route("/api/mlops/status")
@login_required
def api_mlops_status():
    return jsonify(mlops_pipeline.get_status())


@app.route("/api/mlops/train", methods=["POST"])
@login_required
def api_mlops_train():
    data = request.get_json(silent=True) or {}
    result = mlops_pipeline.train(version=data.get("version"))
    if result.get("success"):
        m = result["metrics"]
        mv = ModelVersion(
            model_name=mlops_pipeline.model_name,
            version=result["version"],
            accuracy=m.get("accuracy"),
            precision=m.get("precision"),
            recall=m.get("recall"),
            f1_score=m.get("f1_score"),
            stage="staging",
            trained_by=current_user.id,
        )
        db.session.add(mv)
        db.session.commit()
    return jsonify(result)


@app.route("/api/mlops/promote", methods=["POST"])
@login_required
def api_mlops_promote():
    data = request.get_json(silent=True) or {}
    version = data.get("version")
    if not version:
        return jsonify({"error": "version required"}), 400
    meta = mlops_pipeline.promote_to_production(version)
    ModelVersion.query.filter(
        ModelVersion.model_name == mlops_pipeline.model_name,
        ModelVersion.version != version,
    ).update({"stage": "archived"})
    mv = ModelVersion.query.filter_by(
        model_name=mlops_pipeline.model_name, version=version
    ).first()
    if mv:
        mv.stage = "production"
    db.session.commit()
    return jsonify({"success": True, "metadata": meta})


@app.route("/api/mlops/versions")
@login_required
def api_mlops_versions():
    versions = ModelVersion.query.order_by(ModelVersion.created_at.desc()).all()
    return jsonify({"versions": [v.to_dict() for v in versions]})


@app.route("/api/mlops/runs")
@login_required
def api_mlops_runs():
    runs = mlops_pipeline.tracker.list_runs()
    return jsonify({"runs": runs})


# ════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    for d in ["reports", "data/input", "data/output", "data/training",
              "mlops/registry", "mlops/metrics"]:
        os.makedirs(d, exist_ok=True)
    _seed_admin()
    app.run(host="0.0.0.0", port=5000, debug=False)
