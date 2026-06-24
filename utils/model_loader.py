import os
from functools import lru_cache

import joblib
from flask import current_app, has_app_context


def _default_model_path():
    configured = None
    if has_app_context():
        configured = current_app.config.get("MODEL_PATH")
    configured = configured or os.getenv("MODEL_PATH") or os.path.join("ml", "trained_model.pkl")
    if os.path.isabs(configured):
        return configured
    return os.path.abspath(configured)


@lru_cache(maxsize=1)
def load_model(path=None):
    """Load and cache the sklearn category model."""
    model_path = os.path.abspath(path or _default_model_path())
    return joblib.load(model_path)


class LazyModel:
    """Proxy that keeps legacy imports working while loading the model once."""

    def predict(self, values):
        return load_model().predict(values)


model = LazyModel()
