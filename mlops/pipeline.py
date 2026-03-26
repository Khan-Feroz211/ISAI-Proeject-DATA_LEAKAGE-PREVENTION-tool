"""
mlops/pipeline.py
End-to-end ML training pipeline for the DLP content classifier.

Steps
-----
1. Load labelled scan data from the database (or a CSV fallback).
2. Extract features via feature_engineering.extract_features().
3. Train a RandomForest classifier with cross-validation.
4. Evaluate on a held-out test set.
5. Persist the model with joblib.
6. Register the artifact in the ModelRegistry.
7. Log all metrics to MetricsTracker.
"""
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        f1_score,
        precision_score,
        recall_score,
    )
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from mlops.feature_engineering import extract_features, FEATURE_NAMES
from mlops.metrics_tracker import MetricsTracker
from mlops.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class DLPPipeline:
    """
    MLOps training pipeline for the DLP content classifier.

    Parameters
    ----------
    registry_dir : str
        Path where model artifacts are stored.
    metrics_dir : str
        Path where experiment metrics are stored.
    model_name : str
        Logical name for the model in the registry.
    """

    def __init__(
        self,
        registry_dir: str = "./mlops/registry",
        metrics_dir: str = "./mlops/metrics",
        model_name: str = "dlp_classifier",
    ):
        self.registry = ModelRegistry(registry_dir)
        self.tracker = MetricsTracker(metrics_dir)
        self.model_name = model_name
        self._training_data_path = Path("./data/training")
        self._training_data_path.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def train(
        self,
        samples: Optional[List[Tuple[str, int]]] = None,
        version: Optional[str] = None,
    ) -> Dict:
        """
        Train the classifier.

        Parameters
        ----------
        samples : list[(content_str, label)]
            If None, the pipeline loads data from CSV files in ./data/training/.
        version : str, optional
            Version tag (defaults to ISO timestamp).

        Returns
        -------
        dict  – summary with metrics, artifact path, and run id.
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn is not installed"}

        version = version or datetime.now(timezone.utc).strftime("v%Y%m%d_%H%M%S")
        run = self.tracker.start_run(self.model_name)

        try:
            # 1. Load / validate data
            if not samples:
                samples = self._load_training_data()
            if len(samples) < 10:
                raise ValueError(
                    f"Need at least 10 labelled samples, got {len(samples)}"
                )

            X = np.array([extract_features(s[0]) for s in samples], dtype=float)
            y = np.array([int(s[1]) for s in samples])

            run.log_param("n_samples", len(samples))
            run.log_param("n_features", X.shape[1])
            run.log_param("feature_names", FEATURE_NAMES)

            # 2. Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            run.log_param("train_size", len(X_train))
            run.log_param("test_size", len(X_test))

            # 3. Build pipeline
            clf = Pipeline([
                ("scaler", StandardScaler()),
                ("rf", RandomForestClassifier(
                    n_estimators=100,
                    max_depth=12,
                    min_samples_split=4,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                )),
            ])
            run.log_param("model_type", "RandomForestClassifier")
            run.log_param("n_estimators", 100)
            run.log_param("max_depth", 12)

            # 4. Cross-validation
            cv = StratifiedKFold(n_splits=min(5, len(set(y))), shuffle=True, random_state=42)
            cv_scores = cross_val_score(clf, X_train, y_train, cv=cv, scoring="f1")
            run.log_metric("cv_f1_mean", float(cv_scores.mean()))
            run.log_metric("cv_f1_std", float(cv_scores.std()))

            # 5. Fit on full training set
            clf.fit(X_train, y_train)

            # 6. Evaluate on held-out test set
            y_pred = clf.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            report = classification_report(y_test, y_pred, output_dict=True)

            for name, val in [("accuracy", acc), ("precision", prec),
                               ("recall", rec), ("f1_score", f1)]:
                run.log_metric(name, float(val))

            # 7. Persist artifact
            with tempfile.TemporaryDirectory() as tmp:
                artifact_path = os.path.join(tmp, f"{self.model_name}_{version}.joblib")
                joblib.dump(clf, artifact_path)

                # 8. Register
                metrics = {
                    "accuracy": round(acc, 4),
                    "precision": round(prec, 4),
                    "recall": round(rec, 4),
                    "f1_score": round(f1, 4),
                    "cv_f1_mean": round(float(cv_scores.mean()), 4),
                }
                meta = self.registry.register(
                    model_name=self.model_name,
                    version=version,
                    artifact_path=artifact_path,
                    metrics=metrics,
                    params={"n_estimators": 100, "max_depth": 12},
                    description=f"Auto-trained on {len(samples)} samples",
                    stage="staging",
                )

            run.log_artifact(meta["artifact"])
            run.set_tag("version", version)
            run.end("finished")

            logger.info("Training complete – version=%s, F1=%.3f", version, f1)
            return {
                "success": True,
                "run_id": run.run_id,
                "version": version,
                "metrics": metrics,
                "report": report,
                "artifact": meta["artifact"],
            }

        except Exception as exc:  # pragma: no cover
            run.end("failed")
            logger.error("Training failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    def promote_to_production(self, version: str) -> Dict:
        """Promote a staging version to production in the registry."""
        # First archive any current production version
        for v in self.registry.list_versions(self.model_name):
            if v.get("stage") == "production":
                self.registry.promote(self.model_name, v["version"], "archived")
        return self.registry.promote(self.model_name, version, "production")

    def load_production_model(self):
        """Load and return the current production model (or None)."""
        meta = self.registry.get_production_version(self.model_name)
        if not meta:
            return None
        artifact = meta.get("artifact")
        if artifact and Path(artifact).exists():
            return joblib.load(artifact)
        return None

    def get_status(self) -> Dict:
        """Return a summary suitable for the MLOps dashboard."""
        versions = self.registry.list_versions(self.model_name)
        runs = self.tracker.list_runs(self.model_name)
        production = self.registry.get_production_version(self.model_name)
        best = self.tracker.get_best_run(self.model_name, "f1_score")
        return {
            "model_name": self.model_name,
            "total_versions": len(versions),
            "total_runs": len(runs),
            "production_version": production.get("version") if production else None,
            "production_metrics": production.get("metrics") if production else {},
            "best_run_f1": best["metrics"]["f1_score"][-1]["value"] if best else None,
            "versions": versions,
            "recent_runs": runs[:5],
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_training_data(self) -> List[Tuple[str, int]]:
        """
        Load labelled samples from CSV files in ./data/training/.
        CSV columns: ``content,label``  (label: 1=sensitive, 0=clean)
        """
        samples = []
        csv_files = list(self._training_data_path.glob("*.csv"))
        if not csv_files:
            logger.warning("No training CSV files found in %s", self._training_data_path)
            return samples

        try:
            import pandas as pd
            for csv_path in csv_files:
                df = pd.read_csv(csv_path)
                if "content" in df.columns and "label" in df.columns:
                    for _, row in df.iterrows():
                        if not isinstance(row["content"], str):
                            continue
                        samples.append((str(row["content"]), int(row["label"])))
        except ImportError:
            logger.error("pandas not available – cannot load training CSV")
        return samples
