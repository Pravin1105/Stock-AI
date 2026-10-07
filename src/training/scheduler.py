"""Background training job coordinator and execution status tracker."""

import threading
from datetime import datetime
from typing import Any, Dict, Optional

from src.training.trainer import ModelTrainer, TrainingJobResult


class TrainingScheduler:
    """Coordinates asynchronous or manual model training jobs without blocking API requests."""

    _instance: Optional["TrainingScheduler"] = None

    def __init__(self, trainer: Optional[ModelTrainer] = None) -> None:
        self.trainer = trainer or ModelTrainer()
        self._lock = threading.Lock()
        self.is_running = False
        self.last_run_time: Optional[str] = None
        self.last_status: str = "idle"
        self.last_result: Optional[Dict[str, Any]] = None
        self.last_error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "TrainingScheduler":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def get_status(self) -> Dict[str, Any]:
        """Return the current scheduler execution state and last job outcome."""
        return {
            "is_running": self.is_running,
            "last_status": self.last_status,
            "last_run_time": self.last_run_time,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }

    def _execute_sync(self, **kwargs) -> Dict[str, Any]:
        with self._lock:
            self.is_running = True
            self.last_status = "running"
            self.last_run_time = datetime.utcnow().isoformat() + "Z"
            self.last_error = None

        try:
            result: TrainingJobResult = self.trainer.run_training_job(**kwargs)
            res_dict = result.to_dict()
            with self._lock:
                self.is_running = False
                self.last_status = result.status
                self.last_result = res_dict
            return res_dict
        except Exception as e:
            with self._lock:
                self.is_running = False
                self.last_status = "failed"
                self.last_error = str(e)
                self.last_result = None
            return {
                "status": "failed",
                "promoted": False,
                "error": str(e),
            }

    def trigger_job(self, background: bool = True, **kwargs) -> Dict[str, Any]:
        """Trigger a model training job.

        If background=True, launches in a detached daemon thread and immediately returns
        status='running'.
        """
        if self.is_running:
            return {
                "status": "busy",
                "message": "A training job is already in progress.",
                "last_run_time": self.last_run_time,
            }

        if background:
            thread = threading.Thread(
                target=self._execute_sync,
                kwargs=kwargs,
                daemon=True,
            )
            with self._lock:
                self.is_running = True
                self.last_status = "running"
                self.last_run_time = datetime.utcnow().isoformat() + "Z"
                self.last_error = None
            thread.start()
            return {
                "status": "started",
                "message": "Model retraining launched in background.",
                "timestamp": self.last_run_time,
            }
        else:
            return self._execute_sync(**kwargs)
