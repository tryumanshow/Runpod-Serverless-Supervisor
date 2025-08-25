# RunPod Serverless Supervisor

A tool for managing RunPod serverless model scheduling with a Streamlit web interface.

## 🎯 Project Overview

**Problem**: RunPod serverless models suffer from cold start issues, which means they take time to activate when receiving the first request.

**Solution**: This project sends periodic requests to keep serverless models "warm" and ready for inference, significantly reducing response times.

**Architecture**:
- **Streamlit Frontend**: Easy-to-use web interface for configuration
- **Cronjob Scheduler**: Sends periodic requests to RunPod serverless inference servers
- **Slack Integration**: Reports scheduling results and status updates to Slack channels

## 🚀 Quick Start Guide

### 1. Install Dependencies

```bash
# Update pip to the latest version
pip install --upgrade pip

# Create and activate virtual environment for the project
cd runpod-serverless-supervisor
python -m venv runpod-serverless-supervisor
source runpod-serverless-supervisor/bin/activate

# Install runtime dependencies
pip install -e .

# For development (includes code quality tools)
pip install -e ".[dev]"
```

### 2. Environment Setup
```bash
cp template/settings.example.json config/settings.json
cp template/.env.example .env
```

**Configure `config/settings.json`** for UI defaults and available models:
- `ui.max_interval`: Maximum interval allowed in minutes (default: 1440)
- `ui.default_from_time`: Default start time for schedules (default: "07:30")
- `ui.default_to_time`: Default end time for schedules (default: "16:30")
- `ui.default_interval`: Default interval in minutes (default: 60)
- `ui.auto_refresh_seconds`: UI refresh rate in seconds (default: 5)
- `ui.timezone`: Default timezone for scheduling (default: "Asia/Seoul")
- `models`: Array of available RunPod model names to choose from

**Configure `.env` file** with your actual values:

**Required Settings:**
- `RUNPOD_API_KEY`: Your RunPod API key (required)

**Slack Integration (Optional):**
- `SLACK_WEBHOOK_URL`: Slack webhook URL for general notifications
- `SLACK_ENABLED`: Enable/disable Slack notifications (default: true)
- `SLACK_CHANNEL`: Slack channel for notifications (default: #runpod-alerts)
- `SLACK_USERNAME`: Bot username (default: RunPod Supervisor)
- `SLACK_ICON_EMOJI`: Bot emoji (default: :robot_face:)
- `SLACK_BOT_TOKEN`: Bot token for Web API-based threaded messaging
- `SLACK_MENTION_USER`: User ID for critical failure mentions (format: U1234567890)

### 3. Run Web App
```bash
streamlit run web_interface.py
```

It will open automatically in your browser or access http://localhost:8501.

The page may appear as follows:

![Image](./images/streamlit1.png)


## 💻 Usage

### In the Web Interface:

1. **Time Settings**
   - From: Schedule start time (default: 07:30)
   - To: Schedule end time (default: 16:30)
   - Interval: Call interval in minutes (default: 60 minutes)

2. **Model Configuration**
   - Target URL: Enter RunPod endpoint ID
   - Model: Select model to use

3. **Scheduler Control**
   - ▶️ START: Start scheduler
   - ⏹️ STOP: Stop scheduler

4. **Status Monitoring**
   - Real-time active model count
   - Detailed status table for each model

### Example Workflow

Here's how the scheduler works in practice:

1. **Configure and Start**: Set your schedule (e.g., 3:30 AM to 3:33 PM every minute) and press START
2. **Status Updates**: The status table immediately shows "🟢 Running" for your model

![Image](./images/streamlit2.png)

3. **Automatic Scheduling**: Between 3:30 AM and 3:33 PM, requests are sent every minute to keep your serverless model warm
4. **Slack Notifications**: All scheduling activities are logged to Slack in real-time

![Image](./images/slack.png)

5. **Persistent Operation**: The scheduler continues running daily until you stop it or terminate the Streamlit app

## 📊 Features

### Core Functionality
- **Cold Start Prevention**: Keep serverless models warm with periodic requests
- **Real-time Monitoring**: Automatic status updates with live dashboard
- **Multi-model Support**: Schedule multiple models simultaneously
- **Automatic Cronjob Management**: Persists through system restarts
- **Immediate Testing**: Performs connection test immediately on START
- **Configurable Timezone**: Support for multiple timezones worldwide
- **Intuitive UI**: Color-coded status indicators with Streamlit interface

### Advanced Capabilities
- **Enhanced Slack Integration**: Web API-based threaded messaging with mention notifications for critical alerts
- **Parallel Processing**: Optimized concurrent scheduling for improved performance and reduced latency
- **Intelligent Retry Logic**: Automatic retry mechanisms with exponential backoff for API failures
- **Cold Start Handling**: Specialized handling for serverless model initialization delays
- **On-demand Testing**: Immediate model validation capabilities through the web interface

## 📁 Project Structure

```
runpod-serverless-supervisor/
├── web_interface.py         # Streamlit web app (main)
├── runpod_cronjob.py       # Cronjob execution script
├── core/
│   ├── env_settings.py     # Environment & settings management
│   ├── scheduler_manager.py # Scheduler configuration management
│   └── runpod_api.py       # RunPod API client
├── utils/
│   ├── cronjob_utils.py    # Cronjob management utilities
│   └── slack_utils.py      # Slack notification utilities
├── config/
│   ├── settings.json       # UI settings & model list
│   └── scheduler_config.json # Dynamic scheduler state (auto-generated)
├── template/
│   ├── settings.example.json # Settings template file
│   └── .env.example          # Environment variables template
├── .env                    # Environment variables (API keys, Slack config)
├── requirements.txt        # Package dependencies
└── runpod_cronjob.log      # Cronjob execution logs (auto-generated)
```

## ⚙️ Configuration Files

- **`.env`**: Contains API keys and Slack webhook configuration
- **`config/settings.json`**: UI defaults, model list, and timezone settings
- **`config/scheduler_config.json`**: Dynamic scheduler state (auto-generated)

All configurations are managed through the web interface.

### Configuration Reference

#### Environment Variables (.env)
```bash
# Required Configuration
RUNPOD_API_KEY=your_runpod_api_key_here

# Slack Integration (Optional)
SLACK_WEBHOOK_URL=your_slack_webhook_url          # General notifications
SLACK_ENABLED=true
SLACK_CHANNEL=#runpod-alerts
SLACK_USERNAME=RunPod Supervisor
SLACK_BOT_TOKEN=xoxb-your-bot-token-here          # Threaded messaging
SLACK_MENTION_USER=U1234567890                    # Critical alerts
```

#### Application Settings (config/settings.json)
```json
{
  "ui": {
    "max_interval": 1440,
    "default_from_time": "07:30",
    "default_to_time": "16:30",
    "default_interval": 60,
    "timezone": "Asia/Seoul"
  },
  "models": ["model1", "model2", "model3"]
}
```

## 🔧 Troubleshooting

### Common Issues
- **Buttons not responding**: Refresh the page in your browser
- **Cronjob not working**: Check system cron service status with `systemctl status cron`
- **API connection failed**: Verify Target URL and model settings in the web interface
- **Timezone issues**: Check timezone setting in `config/settings.json`
- **Slack notifications not working**: Verify `SLACK_WEBHOOK_URL` in `.env` file

### Logs and Debugging
- **Cronjob logs**: Check `runpod_cronjob.log` for execution details
- **Streamlit logs**: Check terminal output where web app is running
- **Configuration issues**: Verify all files in `config/` directory exist

### Requirements
- **Python**: 3.8 or higher
- **System**: macOS, Linux (Windows with WSL)
- **Dependencies**: All packages listed in `requirements.txt`

## 🚀 Development

### Code Quality Tools
This project uses automated code quality tools:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run code formatting and linting
ruff check .          # Linting
ruff format .         # Formatting
black .               # Additional formatting
isort .               # Import sorting

# Run all pre-commit hooks manually
pre-commit run --all-files

# Security check
bandit -r .
```

### GitHub Actions
The repository includes CI/CD workflows that automatically:
- Run code linting and formatting checks
- Perform security scans
- Validate code quality on every push and PR

## 🔄 Recent Updates

- **Threaded Slack Notifications**: Structured failure alerts and mentions with improved readability through thread organization
- **Parallel Model Processing**: Optimized concurrent scheduling architecture for enhanced performance and reduced latency
- **Cold Start Management**: Automated handling of serverless model initialization delays
- **On-demand Testing**: Immediate model validation capabilities through the web interface
- **Intelligent Retry Logic**: Enhanced error recovery with detailed failure notifications and exponential backoff
- **Time Formatting Improvements**: Consistent time display and optimized timezone handling

---

**Quick Start**: Simply run `streamlit run web_interface.py` to access all features.
