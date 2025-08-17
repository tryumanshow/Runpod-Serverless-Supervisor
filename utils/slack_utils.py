"""Slack notification utilities"""

from datetime import datetime

import pytz
import requests

from core.env_settings import (
    DEFAULT_TIMEZONE,
    get_slack_config,
    get_timezone_abbreviation,
)


def send_slack_notification_immediate(message, is_success=True, message_type="regular"):
    """Send beautifully formatted slack notification using Block Kit"""
    try:
        slack_config = get_slack_config()

        if not slack_config.get("enabled", False) or not slack_config.get(
            "webhook_url"
        ):
            return

        # Create beautiful block-based message
        blocks = create_beautiful_message_blocks(message, is_success, message_type)

        payload = {
            "channel": slack_config.get("channel", "#runpod-alerts"),
            "username": slack_config.get("username", "RunPod Scheduler"),
            "icon_emoji": slack_config.get("icon_emoji", ":robot_face:"),
            "blocks": blocks,
        }

        response = requests.post(slack_config["webhook_url"], json=payload, timeout=10)
        if response.status_code == 200:
            print(f"Slack notification sent: {message[:50]}...")
        else:
            print(f"Slack API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Slack notification error: {e}")


def create_beautiful_message_blocks(message, is_success, message_type):
    """Create beautiful Slack message blocks"""

    if message_type == "startup":
        # 🚀 Startup message
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 Serverless Instance Started",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
                "accessory": {
                    "type": "image",
                    "image_url": "https://img.icons8.com/color/32/000000/rocket.png",
                    "alt_text": "startup",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🕐 Started at {datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).strftime('%H:%M:%S')} {get_timezone_abbreviation()}",
                    }
                ],
            },
        ]

    elif message_type == "shutdown":
        # 🛑 Shutdown message
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🛑 Daily Operation Ended"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
                "accessory": {
                    "type": "image",
                    "image_url": "https://img.icons8.com/color/32/000000/shutdown.png",
                    "alt_text": "shutdown",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🛌 See you tomorrow! Next start: 07:30:00 {get_timezone_abbreviation()}",
                    }
                ],
            },
        ]

    elif message_type == "test":
        # 🧪 Initial test message
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🧪 *Initial Test Successful*\n{message}",
                },
                "accessory": {
                    "type": "image",
                    "image_url": "https://img.icons8.com/color/32/000000/test-tube.png",
                    "alt_text": "test",
                },
            }
        ]

    else:
        # Regular API success message - more compact and clean
        status_emoji = "✅" if is_success else "❌"
        icon_url = (
            "https://img.icons8.com/color/32/000000/checkmark.png"
            if is_success
            else "https://img.icons8.com/color/32/000000/cancel.png"
        )

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} *API Call {'Successful' if is_success else 'Failed'}*\n{message}",
                },
                "accessory": {
                    "type": "image",
                    "image_url": icon_url,
                    "alt_text": "success" if is_success else "failed",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"⚡ Scheduled execution • {datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).strftime('%H:%M:%S')} {get_timezone_abbreviation()}",
                    }
                ],
            },
        ]
