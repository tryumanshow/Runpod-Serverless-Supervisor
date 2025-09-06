#!/usr/bin/env python3
"""
General RunPod Cronjob Script
Reads active models from scheduler_config.json and processes them
"""

import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from datetime import time as dt_time

import pytz

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Change to script directory for relative imports
os.chdir(script_dir)


MAX_ATTEMPTS = 4
INTERVAL_MINUTES = 5


def _time_prettify(time: datetime) -> str:
    """Format datetime object to readable string format"""
    return time.strftime("%Y-%m-%d %H:%M")


def _extract_endpoint_display(target_url: str) -> str:
    """Extract endpoint ID from RunPod URL for cleaner display"""
    return (
        target_url.split("/v2/")[1].split("/openai")[0]
        if "/v2/" in target_url
        else target_url
    )


def send_slack_notification(message, is_success=True, message_type="regular"):
    """Send notification to Slack if configured"""
    try:
        from utils.slack_utils import send_slack_notification_immediate

        send_slack_notification_immediate(message, is_success, message_type)
    except Exception as e:
        print(f"Slack notification error: {e}")


def handle_cold_start(target_url, model_name, message, tz_abbr):
    """Cold start handling with 4 attempts at 5-minute intervals"""
    from core.env_settings import DEFAULT_TIMEZONE
    from core.runpod_api import make_runpod_request

    tz = pytz.timezone(DEFAULT_TIMEZONE)
    print(f"Starting cold start sequence for {model_name}")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Cold start attempt {attempt}/{MAX_ATTEMPTS} for {model_name}")

        attempt_start_time = datetime.now(tz)
        result = make_runpod_request(target_url, model_name, message)
        attempt_end_time = datetime.now(tz)

        if result.get("success", False):
            # Send success message immediately and exit
            endpoint_display = _extract_endpoint_display(target_url)
            success_message = f"🔥 *Cold Start Successful*\n\n*Model:* `{model_name}`\n*Attempt:* {attempt}/{MAX_ATTEMPTS}\n*Start Time:* {_time_prettify(attempt_start_time)} {tz_abbr}\n*Response Time:* {_time_prettify(attempt_end_time)} {tz_abbr}\n*Endpoint:* <{target_url}|{endpoint_display}>"
            print(f"Cold start successful on attempt {attempt} for {model_name}")
            send_slack_notification(
                success_message, is_success=True, message_type="coldstart"
            )
            return
        else:
            print(f"Cold start attempt {attempt} failed for {model_name}")

            # Wait 5 minutes if not the last attempt
            if attempt < MAX_ATTEMPTS:
                print(f"Waiting {INTERVAL_MINUTES} minutes before next attempt...")
                time.sleep(INTERVAL_MINUTES * 60)  # Wait 5 minutes

    # Send failure message if all 4 attempts failed
    final_failure_time = datetime.now(tz)
    endpoint_display = _extract_endpoint_display(target_url)
    failure_message = f"❄️ *Cold Start Failed*\n\n*Model:* `{model_name}`\n*Total Attempts:* {MAX_ATTEMPTS}\n*Final Attempt Time:* {_time_prettify(final_failure_time)} {tz_abbr}\n*Endpoint:* <{target_url}|{endpoint_display}>\n*Status:* All {MAX_ATTEMPTS} attempts failed"
    print(f"Cold start failed after {MAX_ATTEMPTS} attempts for {model_name}")
    send_slack_notification(failure_message, is_success=False, message_type="coldstart")


def process_single_model(model_name, model_config, now, tz_abbr):
    """Process a single model - designed for parallel execution"""
    try:
        from core.env_settings import DEFAULT_TIMEZONE
        from core.runpod_api import make_runpod_request

        tz = pytz.timezone(DEFAULT_TIMEZONE)

        from_time = model_config.get("from_time", "07:30:00")
        to_time = model_config.get("to_time", "16:30:00")
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

        # Check if this is exactly the start time (send startup notification + cold start)
        if current_t.hour == from_t.hour and current_t.minute == from_t.minute:
            start_date = now.strftime("%Y-%m-%d")
            endpoint_display = _extract_endpoint_display(target_url)
            startup_message = f"*Daily operations started for {start_date}*\n\n*Model:* `{model_name}`\n*Endpoint:* <{target_url}|{endpoint_display}>\n*Schedule:* {from_time} ~ {to_time} {tz_abbr}\n*Interval:* Every {interval_minutes} minutes"
            print(f"Sending startup notification for {model_name}")
            send_slack_notification(
                startup_message, is_success=True, message_type="startup"
            )

            # Cold start sequence for the first API call of the day
            cold_start_message = (
                f"Cold start sequence - {_time_prettify(now)} {tz_abbr}"
            )
            print(f"Starting cold start sequence for {model_name}")
            handle_cold_start(target_url, model_name, cold_start_message, tz_abbr)
            return f"Cold start completed for {model_name}"

        # Check if this is just after the end time (send termination notification once)
        if (current_t.hour == to_t.hour and current_t.minute == to_t.minute + 1) or (
            to_t.minute == 59
            and current_t.hour == to_t.hour + 1
            and current_t.minute == 0
        ):
            end_date = now.strftime("%Y-%m-%d")
            message = f"*Daily operation completed for {end_date}*\n\n*Model:* `{model_name}`\n*Schedule:* {from_time} ~ {to_time} {tz_abbr}\n*Next Start:* Tomorrow at {from_time} {tz_abbr}"
            print(f"Sending end-of-day notification for {model_name}")
            send_slack_notification(message, is_success=True, message_type="shutdown")

        if not in_time_range:
            print(f"Skipping {model_name} - outside time range {from_time} ~ {to_time}")
            return f"Skipped {model_name} - outside time range"

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
                f"Making API call for {model_name} at {_time_prettify(scheduled_start_time)}"
            )

            result = make_runpod_request(
                target_url,
                model_name,
                f"Scheduled API call - {_time_prettify(scheduled_start_time)} {tz_abbr}",
            )

            response_arrival_time = datetime.now(tz)

            if result.get("success", False):
                endpoint_display = _extract_endpoint_display(target_url)
                message = f"*Scheduled Start Time:* {_time_prettify(scheduled_start_time)} {tz_abbr}\n*Response Arrival Time:* {_time_prettify(response_arrival_time)} {tz_abbr}\n*Model:* `{model_name}`\n*Endpoint:* <{target_url}|{endpoint_display}>\n*Schedule:* Every {interval_minutes} minutes ({from_time} ~ {to_time})"
                print("API call successful - sending Slack notification")
                send_slack_notification(
                    message, is_success=True, message_type="regular"
                )
                return f"API call successful for {model_name}"
            else:
                endpoint_display = _extract_endpoint_display(target_url)
                message = f"*Scheduled Start Time:* {_time_prettify(scheduled_start_time)} {tz_abbr}\n*Response Failure Time:* {_time_prettify(response_arrival_time)} {tz_abbr}\n*Model:* `{model_name}`\n*Endpoint:* <{target_url}|{endpoint_display}>\n*Error:* API call failed"
                print(
                    "API call failed - sending Slack notification via Web API for threading"
                )

                # Send failure notification via Web API to get message timestamp
                try:
                    from utils.slack_utils import (
                        send_failure_notification_with_thread,
                        send_mention_notification,
                    )

                    # Send failure message and get timestamp for threading
                    message_ts = send_failure_notification_with_thread(
                        message, model_name
                    )

                    # Send mention notification as thread reply if we got timestamp
                    if message_ts:
                        send_mention_notification(
                            context_message=f"API call failed for model: `{model_name}`",
                            thread_ts=message_ts,
                        )
                    else:
                        # Fallback to regular mention if timestamp not available
                        send_mention_notification(
                            context_message=f"API call failed for model: `{model_name}`"
                        )

                except Exception as e:
                    print(f"Failed to send failure notification with thread: {e}")

                return f"API call failed for {model_name}"
        else:
            print(
                f"Skipping {model_name} - not scheduled to run this minute (interval: {interval_minutes} min, current: {current_minute})"
            )
            return f"Skipped {model_name} - not scheduled"

    except Exception as e:
        error_msg = f"Error processing {model_name}: {e}"
        print(error_msg)
        print(f"Traceback: {traceback.format_exc()}")
        return error_msg


def main():
    try:
        print(f"Script directory: {os.getcwd()}")
        print(f"Python path: {sys.path[:3]}")  # Show first 3 entries

        from core.env_settings import DEFAULT_TIMEZONE

        tz = pytz.timezone(DEFAULT_TIMEZONE)
        print(f"[{_time_prettify(datetime.now(tz))}] Starting cronjob execution...")

        print("Successfully imported make_runpod_request")

        # Load active models from config
        config_path = os.path.join(
            os.path.dirname(__file__), "config/scheduler_config.json"
        )
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        from core.env_settings import get_timezone_abbreviation

        now = datetime.now(tz)
        tz_abbr = get_timezone_abbreviation()
        print(f"Current time: {_time_prettify(now)} {tz_abbr}")

        # Get active models using list comprehension
        active_models = [
            (name, config)
            for name, config in config.get("models", {}).items()
            if config.get("active", False)
        ]
        print(f"Active models: {[name for name, _ in active_models]}")

        # Load settings to get total model count for thread pool sizing
        settings_path = os.path.join(os.path.dirname(__file__), "config/settings.json")
        try:
            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)
            total_models_count = len(settings.get("models", []))
        except (FileNotFoundError, json.JSONDecodeError):
            total_models_count = 10  # Fallback to 10 if settings file is not found

        # Process active models in parallel using ThreadPoolExecutor
        if active_models:
            max_workers = min(
                len(active_models), total_models_count
            )  # Limit to total available models
            print(
                f"Processing {len(active_models)} models with {max_workers} workers (total models: {total_models_count})"
            )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all model processing tasks
                future_to_model = {
                    executor.submit(
                        process_single_model, model_name, model_config, now, tz_abbr
                    ): model_name
                    for model_name, model_config in active_models
                }

                # Process completed tasks as they finish
                for future in as_completed(future_to_model):
                    model_name = future_to_model[future]
                    try:
                        result = future.result()
                        print(f"Model {model_name} processing result: {result}")
                    except Exception as exc:
                        print(f"Model {model_name} generated an exception: {exc}")
        else:
            print("No active models found")

    except Exception as e:
        print(f"Exception occurred: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        try:
            from core.env_settings import DEFAULT_TIMEZONE, get_timezone_abbreviation

            tz = pytz.timezone(DEFAULT_TIMEZONE)
            now_with_tz = datetime.now(tz)
            tz_abbr = get_timezone_abbreviation()
            error_message = f"Serverless API call failed at {_time_prettify(now_with_tz)} {tz_abbr}\nError: {str(e)}"
            send_slack_notification(error_message, is_success=False)
        except Exception:
            pass


if __name__ == "__main__":
    main()
