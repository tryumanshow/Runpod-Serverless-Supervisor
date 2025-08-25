"""Simple RunPod API client using requests"""

from datetime import datetime
from typing import Any, Dict

import pytz
import requests

from .env_settings import DEFAULT_TIMEZONE, get_runpod_api_key


def make_runpod_request(
    target_url: str, model_name: str, message: str = "API CALL TEST"
) -> Dict[str, Any]:
    """Make a request to RunPod OpenAI chat completions API"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_runpod_api_key().replace('Bearer ', '')}",
        }

        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": message}],
            "temperature": 0.9,
        }

        print(f"Making request to {target_url} with model {model_name}")

        response = requests.post(target_url, headers=headers, json=data, timeout=600)

        if response.status_code == 200:
            result = {
                "success": True,
                "timestamp": datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).isoformat(),
                "model": model_name,
                "target_url": target_url,
                "message": message,
                "response": response.text,
                "status_code": response.status_code,
            }

            # Update model status to "running" on first successful call
            from .scheduler_manager import get_active_models, update_model_status

            active_models = get_active_models()
            if (
                model_name in active_models
                and active_models[model_name].get("status") == "testing"
            ):
                update_model_status(model_name, "running")
                print(f"✅ Updated {model_name} status: testing → running")

        else:
            result = {
                "success": False,
                "timestamp": datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).isoformat(),
                "model": model_name,
                "target_url": target_url,
                "message": message,
                "error": f"HTTP {response.status_code}: {response.text}",
                "status_code": response.status_code,
            }

            # Update model status to "error" on failed call
            from .scheduler_manager import get_active_models, update_model_status

            active_models = get_active_models()
            if (
                model_name in active_models
                and active_models[model_name].get("status") == "testing"
            ):
                update_model_status(model_name, "error")
                print(f"❌ Updated {model_name} status: testing → error")

        print(
            f"Request {'successful' if result['success'] else 'failed'} for {model_name}"
        )
        return result

    except Exception as e:
        result = {
            "success": False,
            "timestamp": datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).isoformat(),
            "model": model_name,
            "target_url": target_url,
            "message": message,
            "error": str(e),
            "error_type": type(e).__name__,
        }

        # Update model status to "error" on exception
        try:
            from .scheduler_manager import get_active_models, update_model_status

            active_models = get_active_models()
            if (
                model_name in active_models
                and active_models[model_name].get("status") == "testing"
            ):
                update_model_status(model_name, "error")
                print(f"❌ Updated {model_name} status: testing → error (exception)")
        except Exception:
            pass  # Don't fail the main function if status update fails

        print(f"Request failed for {model_name}: {str(e)}")
        return result
