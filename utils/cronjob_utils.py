"""Cronjob management utilities"""

import os
import subprocess


def get_project_paths():
    """Get project paths for consistency"""
    # Use file-based path resolution instead of cwd to ensure stability
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Try to use virtual environment python if available, fallback to system python
    venv_python = os.path.join(
        project_root, "runpod-serverless-supervisor", "bin", "python"
    )
    if os.path.exists(venv_python):
        python_path = venv_python
    else:
        raise FileNotFoundError(
            "Python executable not found. Neither virtual environment python nor system python3 exists."
        )

    return project_root, python_path


def setup_general_cronjob() -> bool:
    """Setup single general cronjob that handles all models dynamically"""
    try:
        project_root, python_path = get_project_paths()
        script_path = f"{project_root}/runpod_cronjob.py"

        # Single cronjob runs every minute but script handles individual model schedules
        # Use full absolute paths for reliable execution (no cd needed)
        cron_command = f"*/1 * * * * {python_path} {script_path} >> {project_root}/runpod_cronjob.log 2>&1 # runpod_scheduler"

        # Get current crontab
        try:
            current_cron = subprocess.check_output(
                ["crontab", "-l"], stderr=subprocess.DEVNULL
            ).decode()
        except subprocess.CalledProcessError:
            current_cron = ""

        # Remove existing RunPod cronjobs completely to prevent duplicates
        lines = []
        for line in current_cron.split("\n"):
            if line.strip() and not (
                "runpod_cronjob.py" in line or "runpod_scheduler" in line
            ):
                lines.append(line)

        # Check if this exact cronjob already exists to prevent duplicates
        if cron_command.split(" # ")[0] not in [line.split(" # ")[0] for line in lines]:
            lines.append(cron_command)

        # Update crontab
        new_cron = "\n".join([line for line in lines if line.strip()])
        if new_cron and not new_cron.endswith("\n"):
            new_cron += "\n"
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_cron)

        return process.returncode == 0
    except Exception as e:
        print(f"Error setting up general cronjob: {e}")
        return False


def test_immediate_cronjob(model_name: str) -> bool:
    """Test single model immediately regardless of time settings"""
    try:
        from datetime import datetime

        import pytz

        from core.runpod_api import make_runpod_request
        from core.scheduler_manager import get_model_config
        from utils.slack_utils import send_slack_notification_immediate

        # Get model configuration
        model_config = get_model_config(model_name)
        if not model_config:
            return False

        target_url = model_config.get("target_url", "")
        if not target_url:
            return False

        # Make immediate API call for testing
        result = make_runpod_request(
            target_url, model_name, f"Initial test - {model_name}"
        )
        success = result.get("success", False)

        # Send Slack notification for immediate test
        if success:
            from core.env_settings import DEFAULT_TIMEZONE

            tz = pytz.timezone(DEFAULT_TIMEZONE)
            call_time = datetime.now(tz)
            interval_minutes = model_config.get("interval_minutes", 1)
            from_time = model_config.get("from_time", "08:30:00")
            to_time = model_config.get("to_time", "17:30:00")

            from core.env_settings import get_timezone_abbreviation

            tz_abbr = get_timezone_abbreviation()
            message = f"Initial test successful at {call_time.strftime('%Y-%m-%d %H:%M')} {tz_abbr}\nModel: `{model_name}`\nEndpoint: `{target_url}`\nScheduled: Every {interval_minutes} minutes ({from_time} ~ {to_time})"
            send_slack_notification_immediate(
                message, is_success=True, message_type="test"
            )

        return success

    except Exception as e:
        print(f"Error testing {model_name}: {e}")
        return False


def remove_all_cronjobs() -> bool:
    """Remove all RunPod cronjobs"""
    try:
        # Get current crontab
        try:
            current_cron = subprocess.check_output(
                ["crontab", "-l"], stderr=subprocess.DEVNULL
            ).decode()
        except subprocess.CalledProcessError:
            return True  # No crontab exists, consider it success

        # Remove all RunPod jobs (both old individual and scheduler)
        lines = [
            line
            for line in current_cron.split("\n")
            if not any(tag in line for tag in ["# runpod_", "# runpod_scheduler"])
        ]

        # Update crontab
        new_cron = "\n".join([line for line in lines if line.strip()])
        if new_cron and not new_cron.endswith("\n"):
            new_cron += "\n"
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_cron)

        # Remove old script files
        try:
            project_root, _ = get_project_paths()
            import glob

            for script_file in glob.glob(f"{project_root}/cron_runpod_*.py"):
                os.remove(script_file)
        except (OSError, FileNotFoundError):
            pass

        return process.returncode == 0
    except Exception as e:
        print(f"Error removing cronjobs: {e}")
        return False
