"""Model Registry managing versions, performance metadata, and active deployment pointers."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import xgboost as xgb

from src.core.config import settings


class ModelRegistry:
    """Manages versioned storage and active pointer for trained forecasting models.

    Resilient to read-only environments (e.g. AWS Lambda / Vercel Serverless Functions).
    """

    _instance: Optional["ModelRegistry"] = None

    def __init__(self, registry_dir: Optional[Path] = None) -> None:
        self.model_dir = registry_dir or settings.model_dir
        self.versions_dir = self.model_dir / "versions"
        self.registry_file = self.model_dir / "registry.json"
        self.active_symlink_file = self.model_dir / "tuned_xgboost_model.json"

        self.is_writable: bool = False
        self._in_memory_data: Optional[Dict[str, Any]] = None

        # Verify whether model directory is writable; fallback gracefully in serverless read-only runtimes
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.model_dir / f".write_test_{os.getpid()}"
            test_file.touch()
            test_file.unlink()
            self.versions_dir.mkdir(parents=True, exist_ok=True)
            self.is_writable = True
        except (OSError, PermissionError):
            self.is_writable = False
            self.versions_dir = Path(tempfile.gettempdir()) / "model_versions"
            try:
                self.versions_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        self._ensure_initialized()

    @classmethod
    def get_instance(cls, registry_dir: Optional[Path] = None) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = cls(registry_dir=registry_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def _ensure_initialized(self) -> None:
        """Seed registry with incumbent model metadata, in-memory or on-disk."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    self._in_memory_data = json.load(f)
                    return
            except Exception:
                pass

        initial_records = []
        active_version = None

        if self.active_symlink_file.exists():
            version = "v1.0.0"
            target_save = self.versions_dir / f"{version}.json"
            if self.is_writable and not target_save.exists():
                try:
                    import shutil
                    shutil.copyfile(self.active_symlink_file, target_save)
                except Exception:
                    pass

            initial_records.append({
                "version": version,
                "status": "active_champion",
                "model_path": str(self.active_symlink_file),
                "trained_at": "2026-09-17T22:26:00Z",
                "promoted_at": "2026-09-17T22:26:00Z",
                "metrics": {
                    "smape": 6.193,
                    "mae": 5.866,
                    "rmse": 7.619,
                    "wape": 10.738,
                },
                "dataset_info": {
                    "source": "train.csv",
                    "rows": 913000,
                    "date_range": "2013-01-01 to 2017-12-31",
                },
                "notes": "Baseline tuned XGBoost from v1.0",
            })
            active_version = version

        data = {
            "active_version": active_version,
            "models": initial_records,
        }
        self._in_memory_data = data

        if self.is_writable:
            try:
                with open(self.registry_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except (OSError, PermissionError):
                pass

    def _load_data(self) -> Dict[str, Any]:
        if self._in_memory_data is not None:
            return self._in_memory_data

        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    self._in_memory_data = json.load(f)
                    return self._in_memory_data
            except Exception:
                pass

        self._ensure_initialized()
        return self._in_memory_data or {"active_version": None, "models": []}

    def _save_data(self, data: Dict[str, Any]) -> None:
        self._in_memory_data = data
        if self.is_writable:
            try:
                with open(self.registry_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except (OSError, PermissionError):
                pass

    def get_active_model_path(self) -> Path:
        """Return the path to the currently active model."""
        return self.active_symlink_file

    def get_active_version(self) -> Optional[str]:
        data = self._load_data()
        return data.get("active_version")

    def load_active_booster(self) -> Optional[xgb.Booster]:
        """Load and return the active champion model booster."""
        if not self.active_symlink_file.exists():
            return None
        booster = xgb.Booster()
        booster.load_model(str(self.active_symlink_file))
        return booster

    def promote_candidate(
        self,
        booster: xgb.Booster,
        metrics: Dict[str, Any],
        dataset_info: Dict[str, Any],
        notes: str = "",
    ) -> str:
        """Save candidate booster as the new active champion in registry."""
        data = self._load_data()
        existing_versions = [m["version"] for m in data.get("models", [])]

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        version_num = len(existing_versions) + 1
        new_version = f"v{version_num}.0.0_{timestamp}"

        version_file = self.versions_dir / f"{new_version}.json"
        booster.save_model(str(version_file))

        # Copy to active_symlink_file if root is writable
        if self.is_writable:
            try:
                booster.save_model(str(self.active_symlink_file))
            except (OSError, PermissionError):
                pass

        # Archive prior champions
        for m in data.get("models", []):
            if m.get("status") == "active_champion":
                m["status"] = "archived"

        try:
            rel_path = str(version_file.relative_to(settings.base_dir))
        except ValueError:
            rel_path = str(version_file)

        record = {
            "version": new_version,
            "status": "active_champion",
            "model_path": rel_path,
            "trained_at": datetime.utcnow().isoformat() + "Z",
            "promoted_at": datetime.utcnow().isoformat() + "Z",
            "metrics": metrics,
            "dataset_info": dataset_info,
            "notes": notes,
        }
        data["models"].append(record)
        data["active_version"] = new_version
        self._save_data(data)

        return new_version

    def record_rejected(
        self,
        booster: xgb.Booster,
        metrics: Dict[str, Any],
        dataset_info: Dict[str, Any],
        reason: str,
    ) -> str:
        """Save rejected candidate for audit trail and tracking without promoting."""
        data = self._load_data()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        new_version = f"candidate_rejected_{timestamp}"

        version_file = self.versions_dir / f"{new_version}.json"
        booster.save_model(str(version_file))

        try:
            rel_path = str(version_file.relative_to(settings.base_dir))
        except ValueError:
            rel_path = str(version_file)

        record = {
            "version": new_version,
            "status": "rejected",
            "model_path": rel_path,
            "trained_at": datetime.utcnow().isoformat() + "Z",
            "rejection_reason": reason,
            "metrics": metrics,
            "dataset_info": dataset_info,
        }
        data["models"].append(record)
        self._save_data(data)

        return new_version

    def list_models(self) -> List[Dict[str, Any]]:
        """Return all registered model records."""
        data = self._load_data()
        return data.get("models", [])
