"""Simple configuration management"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import pytz

from .env_settings import DEFAULT_TIMEZONE

CONFIG_FILE = "config/scheduler_config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file"""
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return {}


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except (OSError, json.JSONEncodeError, PermissionError):
        return False


def get_active_models() -> Dict[str, Dict[str, Any]]:
    """Get all active model configurations"""
    config = load_config()
    models = config.get("models", {})
    return {
        name: model_config
        for name, model_config in models.items()
        if model_config.get("active", False)
    }


def get_model_config(model_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific model"""
    config = load_config()
    models = config.get("models", {})
    return models.get(model_name)


def set_model_config(
    model_name: str,
    target_url: str,
    from_time: str,
    to_time: str,
    interval_minutes: int,
    active: bool = True,
    status: str = "running",
) -> bool:
    """Set configuration for a model"""
    config = load_config()

    if "models" not in config:
        config["models"] = {}

    config["models"][model_name] = {
        "target_url": target_url,
        "from_time": from_time,
        "to_time": to_time,
        "interval_minutes": interval_minutes,
        "active": active,
        "status": status,  # "testing", "running", "stopped"
        "last_updated": datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).isoformat(),
    }

    return save_config(config)


def deactivate_model(model_name: str) -> bool:
    """Deactivate scheduling for a model"""
    config = load_config()
    if "models" in config and model_name in config["models"]:
        config["models"][model_name]["active"] = False
        config["models"][model_name]["status"] = "stopped"
        config["models"][model_name]["last_updated"] = datetime.now(
            pytz.timezone(DEFAULT_TIMEZONE)
        ).isoformat()
        return save_config(config)
    return False


def update_model_status(model_name: str, status: str) -> bool:
    """Update status of a model (testing -> running)"""
    config = load_config()
    if "models" in config and model_name in config["models"]:
        config["models"][model_name]["status"] = status
        config["models"][model_name]["last_updated"] = datetime.now(
            pytz.timezone(DEFAULT_TIMEZONE)
        ).isoformat()
        return save_config(config)
    return False
