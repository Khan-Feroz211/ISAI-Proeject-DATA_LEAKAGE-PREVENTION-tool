"""
mlops/metrics_tracker.py
Lightweight experiment & metrics tracker (MLflow-compatible interface).
Persists run data as JSON files so no external service is required.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class Run:
    """Represents a single experiment run."""

    def __init__(self, run_id: str, experiment_name: str, metrics_dir: Path):
        self.run_id = run_id
        self.experiment_name = experiment_name
        self._metrics_dir = metrics_dir
        self._data: Dict[str, Any] = {
            "run_id": run_id,
            "experiment": experiment_name,
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "params": {},
            "metrics": {},
            "artifacts": [],
            "tags": {},
        }
        self._save()

    # ── Public API ────────────────────────────────────────────────────────────

    def log_param(self, key: str, value: Any):
        self._data["params"][key] = value
        self._save()

    def log_metric(self, key: str, value: float, step: Optional[int] = None):
        if key not in self._data["metrics"]:
            self._data["metrics"][key] = []
        entry = {"value": value, "step": step, "ts": datetime.now(timezone.utc).isoformat()}
        self._data["metrics"][key].append(entry)
        self._save()

    def log_artifact(self, path: str):
        self._data["artifacts"].append(path)
        self._save()

    def set_tag(self, key: str, value: str):
        self._data["tags"][key] = value
        self._save()

    def end(self, status: str = "finished"):
        self._data["status"] = status
        self._data["end_time"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def get_metric(self, key: str) -> Optional[float]:
        entries = self._data["metrics"].get(key, [])
        return entries[-1]["value"] if entries else None

    def to_dict(self) -> Dict:
        return dict(self._data)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _save(self):
        self._metrics_dir.mkdir(parents=True, exist_ok=True)
        path = self._metrics_dir / f"{self.run_id}.json"
        path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")


class MetricsTracker:
    """
    Simple experiment tracker.

    Usage
    -----
    tracker = MetricsTracker()
    with tracker.start_run("dlp_classifier_v2") as run:
        run.log_param("n_estimators", 100)
        run.log_metric("accuracy", 0.93)
    """

    def __init__(self, metrics_dir: str = "./mlops/metrics"):
        self._metrics_dir = Path(metrics_dir)
        self._metrics_dir.mkdir(parents=True, exist_ok=True)

    def start_run(self, experiment_name: str) -> Run:
        run_id = str(uuid.uuid4())[:8]
        return Run(run_id, experiment_name, self._metrics_dir)

    def list_runs(self, experiment_name: Optional[str] = None) -> list:
        runs = []
        for f in sorted(self._metrics_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if experiment_name is None or data.get("experiment") == experiment_name:
                    runs.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return runs

    def get_best_run(self, experiment_name: str, metric: str, higher_is_better: bool = True):
        """Return the run dict with the best value for *metric*."""
        candidates = [
            r for r in self.list_runs(experiment_name)
            if metric in r.get("metrics", {})
        ]
        if not candidates:
            return None
        key = lambda r: r["metrics"][metric][-1]["value"]  # noqa: E731
        return max(candidates, key=key) if higher_is_better else min(candidates, key=key)
