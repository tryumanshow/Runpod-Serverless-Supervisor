"""Configuration management using python-dotenv"""

import json
import os
from datetime import time as dt_time
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_settings() -> Dict[str, Any]:
    """Load UI and app settings from JSON file"""
    settings_path = Path(__file__).parent.parent / "config" / "settings.json"

    if not settings_path.exists():
        raise ValueError(
            f"settings.json file not found at {settings_path}. Please create the config file or check the path."
        )

    try:
        with open(settings_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"settings.json has invalid JSON syntax at {settings_path}. Error: {e}"
        ) from e


def get_runpod_api_key() -> str:
    """Get RunPod API key from environment"""
    api_key = os.getenv("RUNPOD_API_KEY")
    if not api_key:
        raise ValueError("RUNPOD_API_KEY not found in environment variables")
    return api_key


def get_slack_bot_token() -> str:
    """Get Slack Bot Token from environment variables"""
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    if not bot_token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")
    return bot_token


def get_slack_mention_user() -> str:
    """Get Slack mention user from environment variables"""
    mention_user = os.getenv("SLACK_MENTION_USER", "Seungwoo Ryu")
    return mention_user


def get_slack_config() -> Dict[str, Any]:
    """Get Slack configuration from environment variables"""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    enabled = os.getenv("SLACK_ENABLED", "true").lower() == "true"

    if not webhook_url and enabled:
        print("Warning: SLACK_WEBHOOK_URL not set, disabling Slack notifications")
        enabled = False

    return {
        "webhook_url": webhook_url or "",
        "channel": os.getenv("SLACK_CHANNEL", "#runpod-alerts"),
        "username": os.getenv("SLACK_USERNAME", "RunPod Supervisor"),
        "icon_emoji": os.getenv("SLACK_ICON_EMOJI", ":robot_face:"),
        "enabled": enabled,
    }


# Load settings once when module is imported
SETTINGS = get_settings()
UI_SETTINGS = SETTINGS["ui"]
AVAILABLE_MODELS = SETTINGS["models"]

# UI configuration constants
MAX_INTERVAL = UI_SETTINGS["max_interval"]
DEFAULT_FROM_TIME = dt_time(*map(int, UI_SETTINGS["default_from_time"].split(":")))
DEFAULT_TO_TIME = dt_time(*map(int, UI_SETTINGS["default_to_time"].split(":")))
DEFAULT_INTERVAL = UI_SETTINGS["default_interval"]
AUTO_REFRESH_SECONDS = UI_SETTINGS["auto_refresh_seconds"]
DEFAULT_TIMEZONE = UI_SETTINGS.get("timezone", "Asia/Seoul")


def get_timezone_abbreviation() -> str:
    """Get timezone abbreviation for display purposes"""
    from datetime import datetime

    import pytz

    tz = pytz.timezone(DEFAULT_TIMEZONE)
    now = datetime.now(tz)
    return now.strftime("%Z")
