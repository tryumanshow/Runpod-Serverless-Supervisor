#!/usr/bin/env python3
"""
General RunPod Cronjob Script
Reads active models from scheduler_config.json and processes them
"""
import json
import os
import sys
import traceback

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Change to script directory for relative imports
os.chdir(script_dir)


def send_slack_notification(message, is_success=True, message_type="regular"):
    """Send notification to Slack if configured"""
    try:
        from utils.slack_utils import send_slack_notification_immediate

        send_slack_notification_immediate(message, is_success, message_type)
    except Exception as e:
        print(f"Slack notification error: {e}")


def main():
    try:
        print(f"Script directory: {os.getcwd()}")
        print(f"Python path: {sys.path[:3]}")  # Show first 3 entries

        from datetime import datetime
        from datetime import time as dt_time

        import pytz

        print(f"[{datetime.now()}] Starting cronjob execution...")

        from core.runpod_api import make_runpod_request

        print("Successfully imported make_runpod_request")

        # Load active models from config
        config_path = os.path.join(
            os.path.dirname(__file__), "config/scheduler_config.json"
        )
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        from core.env_settings import DEFAULT_TIMEZONE, get_timezone_abbreviation

        tz = pytz.timezone(DEFAULT_TIMEZONE)
        now = datetime.now(tz)
        tz_abbr = get_timezone_abbreviation()
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} {tz_abbr}")

        # Get active models using list comprehension
        active_models = [
            name
            for name, config in config.get("models", {}).items()
            if config.get("active", False)
        ]
        print(f"Active models: {active_models}")

        # Process only active models
        for model_name, model_config in config.get("models", {}).items():
            if not model_config.get("active", False):
                continue

            from_time = model_config.get("from_time", "08:30:00")
            to_time = model_config.get("to_time", "17:30:00")
            target_url = model_config.get("target_url", "")
            interval_minutes = model_config.get("interval_minutes", 30)

            # Parse time range
            from_t = dt_time.fromisoformat(from_time)
            to_t = dt_time.fromisoformat(to_time)
            current_t = now.time()

            # Check if current time is within the specified range
            in_time_range = (
                (from_t <= current_t <= to_t)
                if from_t <= to_t
                else (current_t >= from_t or current_t <= to_t)
            )

            # Check if this is exactly the start time (send startup notification)
            if current_t.hour == from_t.hour and current_t.minute == from_t.minute:
                start_date = now.strftime("%Y-%m-%d")
                message = f"**Daily operations started for {start_date}**\n\n*Model:* `{model_name}`\n*Endpoint:* `{target_url}`\n*Schedule:* {from_time} ~ {to_time} {tz_abbr}\n*Interval:* Every {interval_minutes} minutes"
                print(f"Sending startup notification for {model_name}")
                send_slack_notification(
                    message, is_success=True, message_type="startup"
                )

            # Check if this is just after the end time (send termination notification once)
            if (
                current_t.hour == to_t.hour and current_t.minute == to_t.minute + 1
            ) or (
                to_t.minute == 59
                and current_t.hour == to_t.hour + 1
                and current_t.minute == 0
            ):
                end_date = now.strftime("%Y-%m-%d")
                message = f"**Daily operation completed for {end_date}**\n\n*Model:* `{model_name}`\n*Schedule:* {from_time} ~ {to_time} {tz_abbr}\n*Next Start:* Tomorrow at {from_time} {tz_abbr}"
                print(f"Sending end-of-day notification for {model_name}")
                send_slack_notification(
                    message, is_success=True, message_type="shutdown"
                )

            if not in_time_range:
                print(
                    f"Skipping {model_name} - outside time range {from_time} ~ {to_time}"
                )
                continue

            # Check if it's time to run based on interval
            current_minute = now.minute
            if interval_minutes == 1:
                should_run = True  # Run every minute
            elif interval_minutes <= 60:
                should_run = current_minute % interval_minutes == 0
            else:
                # For intervals > 60 minutes, check hour and minute
                current_hour = now.hour
                should_run = (
                    current_minute == 0 and current_hour % (interval_minutes // 60) == 0
                )

            if should_run:
                # Record when cronjob scheduling started
                scheduled_start_time = now
                print(
                    f"Making API call for {model_name} at {scheduled_start_time.strftime('%H:%M:%S')}"
                )
                result = make_runpod_request(
                    target_url,
                    model_name,
                    f"Scheduled API call - {scheduled_start_time.strftime('%Y-%m-%d %H:%M:%S')} {tz_abbr}",
                )

                if result.get("success", False):
                    message = f"*Time:* {scheduled_start_time.strftime('%Y-%m-%d %H:%M')} {tz_abbr}\n*Model:* `{model_name}`\n*Endpoint:* `{target_url}`\n*Schedule:* Every {interval_minutes} minutes ({from_time} ~ {to_time})"
                    print("API call successful - sending Slack notification")
                    send_slack_notification(
                        message, is_success=True, message_type="regular"
                    )
                else:
                    message = f"*Time:* {scheduled_start_time.strftime('%Y-%m-%d %H:%M')} {tz_abbr}\n*Model:* `{model_name}`\n*Error:* API call failed"
                    print("API call failed - sending Slack notification")
                    send_slack_notification(
                        message, is_success=False, message_type="regular"
                    )
            else:
                print(
                    f"Skipping {model_name} - not scheduled to run this minute (interval: {interval_minutes} min, current: {current_minute})"
                )

    except Exception as e:
        print(f"Exception occurred: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        try:
            from datetime import datetime

            import pytz

            from core.env_settings import DEFAULT_TIMEZONE, get_timezone_abbreviation

            tz = pytz.timezone(DEFAULT_TIMEZONE)
            now_with_tz = datetime.now(tz)
            tz_abbr = get_timezone_abbreviation()
            error_message = f"Serverless API call failed at {now_with_tz.strftime('%Y-%m-%d %H:%M')} {tz_abbr}\nError: {str(e)}"
            send_slack_notification(error_message, is_success=False)
        except Exception:
            pass


if __name__ == "__main__":
    main()
