"""Slack notification utilities"""

from datetime import datetime

import pytz
import requests

from core.env_settings import (
    DEFAULT_TIMEZONE,
    get_slack_bot_token,
    get_slack_config,
    get_slack_mention_user,
    get_timezone_abbreviation,
)


def _format_slack_mention(mention_user: str) -> str:
    """Format Slack mention based on user ID type"""
    if mention_user.startswith("S"):
        return f"<!subteam^{mention_user}>"  # User group
    elif mention_user.startswith("U"):
        return f"<@{mention_user}>"  # Individual user
    else:
        return f"<!{mention_user}>"  # Channel mentions (here, channel, etc.)


def send_failure_notification_with_thread(message, model_name):
    """Send failure notification via Web API and return message timestamp for threading"""
    try:
        bot_token = get_slack_bot_token()
        slack_config = get_slack_config()

        if not slack_config.get("enabled", False):
            return None

        channel = slack_config.get("channel", "#runpod-alerts")

        # Create failure message blocks
        blocks = create_beautiful_message_blocks(
            message, is_success=False, message_type="regular"
        )

        payload = {
            "channel": channel,
            "blocks": blocks,
            "username": slack_config.get("username", "RunPod Supervisor"),
            "icon_emoji": slack_config.get("icon_emoji", ":robot_face:"),
        }

        headers = {"Authorization": f"Bearer {bot_token}"}
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print(f"Failure notification sent via Web API: {message[:50]}...")
                return result.get("ts")  # Return message timestamp for threading
            else:
                print(f"Failure notification failed: {result.get('error')}")
                return None
        else:
            print(f"Failure notification HTTP error: {response.status_code}")
            return None

    except Exception as e:
        print(f"Failure notification error: {e}")
        return None


def send_mention_notification(
    mention_user=None, context_message="API call failed", thread_ts=None
):
    """Send mention notification using Bot Token, optionally as a thread reply"""
    try:
        bot_token = get_slack_bot_token()
        slack_config = get_slack_config()

        if not slack_config.get("enabled", False):
            return

        # Use environment variable if mention_user not provided
        if mention_user is None:
            mention_user = get_slack_mention_user()

        channel = slack_config.get("channel", "#runpod-alerts")

        common_message = f"*[URGENT]*: {context_message}. Please take appropriate actions to ensure that the customer does not encounter any issues when using this model."
        formatted_mention = _format_slack_mention(mention_user)
        mention_message = f"🚨 {formatted_mention} - {common_message}"

        payload = {
            "channel": channel,
            "text": mention_message,
        }

        # Add thread_ts if provided to make this a thread reply
        if thread_ts:
            payload["thread_ts"] = thread_ts

        headers = {"Authorization": f"Bearer {bot_token}"}
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                thread_info = " (in thread)" if thread_ts else ""
                print(f"Mention notification sent: @{mention_user}{thread_info}")
            else:
                print(f"Mention notification failed: {result.get('error')}")
        else:
            print(f"Mention notification HTTP error: {response.status_code}")

    except Exception as e:
        print(f"Mention notification error: {e}")


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
            "username": slack_config.get("username", "RunPod Supervisor"),
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
            {"type": "divider"},
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
            {"type": "divider"},
        ]

    elif message_type == "shutdown":
        # 🛑 Shutdown message
        return [
            {"type": "divider"},
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
            {"type": "divider"},
        ]

    elif message_type == "test":
        # 🧪 Initial test message
        return [
            {"type": "divider"},
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
            },
            {"type": "divider"},
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
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} API Call {'Successful' if is_success else 'Failed'}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
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
            {"type": "divider"},
        ]
