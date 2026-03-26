"""
mlops/model_registry.py
Versioned model storage backed by the local filesystem.
Each model version is saved with metadata in a JSON sidecar file.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class ModelRegistry:
    """
    Filesystem-backed model registry.

    Directory layout::

        registry/
          dlp_classifier/
            v1/
              model.joblib
              metadata.json
            v2/
              model.joblib
              metadata.json
          anomaly_detector/
            ...
    """

    def __init__(self, registry_dir: str = "./mlops/registry"):
        self._root = Path(registry_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    # ── Write ─────────────────────────────────────────────────────────────────

    def register(
        self,
        model_name: str,
        version: str,
        artifact_path: str,
        metrics: Optional[Dict] = None,
        params: Optional[Dict] = None,
        description: str = "",
        stage: str = "staging",
    ) -> Dict:
        """
        Copy *artifact_path* into the registry and save metadata.
        Returns the metadata dict.
        """
        dest_dir = self._root / model_name / version
        dest_dir.mkdir(parents=True, exist_ok=True)

        src = Path(artifact_path)
        dest_artifact = dest_dir / src.name
        shutil.copy2(str(src), str(dest_artifact))

        metadata = {
            "model_name": model_name,
            "version": version,
            "description": description,
            "stage": stage,
            "artifact": str(dest_artifact),
            "metrics": metrics or {},
            "params": params or {},
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        (dest_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        return metadata

    def promote(self, model_name: str, version: str, stage: str):
        """Change the stage of a version (e.g. staging → production)."""
        meta_path = self._root / model_name / version / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No version '{version}' for model '{model_name}'")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["stage"] = stage
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta

    # ── Read ──────────────────────────────────────────────────────────────────

    def list_versions(self, model_name: str) -> List[Dict]:
        model_dir = self._root / model_name
        if not model_dir.exists():
            return []
        versions = []
        for v_dir in sorted(model_dir.iterdir()):
            meta_path = v_dir / "metadata.json"
            if meta_path.exists():
                try:
                    versions.append(json.loads(meta_path.read_text(encoding="utf-8")))
                except json.JSONDecodeError:
                    continue
        return versions

    def get_production_version(self, model_name: str) -> Optional[Dict]:
        for v in self.list_versions(model_name):
            if v.get("stage") == "production":
                return v
        return None

    def list_models(self) -> List[str]:
        return [d.name for d in sorted(self._root.iterdir()) if d.is_dir()]

    def get_all_versions(self) -> List[Dict]:
        all_versions = []
        for model in self.list_models():
            all_versions.extend(self.list_versions(model))
        return sorted(all_versions, key=lambda v: v.get("registered_at", ""), reverse=True)
