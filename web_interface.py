"""RunPod Serverless Supervisor - Streamlit Web Interface"""

import pandas as pd
import streamlit as st

from core.env_settings import (
    AVAILABLE_MODELS,
    DEFAULT_FROM_TIME,
    DEFAULT_INTERVAL,
    DEFAULT_TO_TIME,
    MAX_INTERVAL,
)
from core.scheduler_manager import deactivate_model, get_active_models, set_model_config
from utils.cronjob_utils import (
    remove_all_cronjobs,
    setup_general_cronjob,
    test_immediate_cronjob,
)

# Page config
st.set_page_config(page_title="RunPod Serverless Supervisor", layout="wide")


# Title with refresh button - same horizontal line
col1, col2 = st.columns([10, 1])
with col1:
    st.title("⏰ RunPod Supervisor")
with col2:
    st.markdown(
        "<div style='margin-top: 1rem; text-align: right;'>", unsafe_allow_html=True
    )
    if st.button("🔄 Refresh", key="top_refresh", use_container_width=True):
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# Initialize session state for messages
if "message" not in st.session_state:
    st.session_state.message = None

# Current active models info
active_configs = get_active_models()
total_active = len(active_configs)

if total_active > 0:
    st.success(f"🟢 Active Models: {total_active}")
else:
    st.info("💤 No active models")

st.markdown("---")
st.markdown("### ⏰ Time Settings")

# Time settings
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("##### From")
    from_time = st.time_input(
        "From", value=DEFAULT_FROM_TIME, label_visibility="collapsed", step=60
    )

with col2:
    st.markdown("##### To")
    to_time = st.time_input(
        "To", value=DEFAULT_TO_TIME, label_visibility="collapsed", step=60
    )

with col3:
    st.markdown("##### Interval (min)")
    interval_value = st.number_input(
        "Interval",
        min_value=1,
        max_value=MAX_INTERVAL,
        value=DEFAULT_INTERVAL,
        label_visibility="collapsed",
        help=f"Maximum configurable time interval is 24 hours ({MAX_INTERVAL} minutes).",
    )

st.markdown("---")

# Control panel
st.markdown("### 🎮 Control Panel")

url = st.text_input("Target URL", placeholder="Your RunPod endpoint ID")
# Ensure consistent URL format for OpenAI chat completions endpoint
if url:
    url = url.strip()
    if url.startswith("https://"):
        target_url = url
    else:
        target_url = f"https://api.runpod.ai/v2/{url}/openai/v1/chat/completions"
else:
    target_url = ""
model_repo = st.selectbox("Model", options=AVAILABLE_MODELS, index=0)
run_initial_test = st.checkbox(
    "Run initial test after setup",
    value=False,
    help="Test the endpoint immediately after starting",
)

# Start/Stop buttons
col1, col2 = st.columns(2)

with col1:
    start_pressed = st.button(
        "▶️ START", type="primary", use_container_width=True, key=f"start_{model_repo}"
    )

# Handle start button
if start_pressed:
    if url and model_repo:
        # Save config with "running" status directly
        config_success = set_model_config(
            model_name=model_repo,
            target_url=target_url,
            from_time=from_time.strftime("%H:%M:%S"),
            to_time=to_time.strftime("%H:%M:%S"),
            interval_minutes=interval_value,
            active=True,
            status="running",
        )

        if config_success:
            # Setup single general cronjob (handles all models)
            cronjob_success = setup_general_cronjob()

            if cronjob_success:
                if run_initial_test:
                    # Run immediate test
                    test_success = test_immediate_cronjob(model_repo)

                    if test_success:
                        st.session_state.message = (
                            "success",
                            f"✅ Started {model_repo} - Initial test successful! Running every {interval_value} minutes from {from_time.strftime('%H:%M')} to {to_time.strftime('%H:%M')}",
                        )
                    else:
                        st.session_state.message = (
                            "warning",
                            f"⚠️ Started {model_repo} but initial test failed - Check your endpoint URL",
                        )
                else:
                    st.session_state.message = (
                        "success",
                        f"✅ Started {model_repo}! Running every {interval_value} minutes from {from_time.strftime('%H:%M')} to {to_time.strftime('%H:%M')}",
                    )
            else:
                st.session_state.message = (
                    "error",
                    "❌ Failed to setup cronjob system",
                )
        else:
            st.session_state.message = ("error", "Failed to save config")
    else:
        st.session_state.message = ("error", "Please enter URL and select model")
    st.rerun()

with col2:
    stop_pressed = st.button(
        "⏹️ STOP", type="secondary", use_container_width=True, key=f"stop_{model_repo}"
    )

# Handle stop button
if stop_pressed:
    if model_repo:
        # Remove from config (but keep general cronjob for other active models)
        config_success = deactivate_model(model_repo)

        # Check if there are any other active models
        active_configs = get_active_models()
        has_other_active = any(m != model_repo for m in active_configs)

        cronjob_success = True
        if not has_other_active:
            # Remove all cronjobs if no active models
            cronjob_success = remove_all_cronjobs()

        if config_success:
            if has_other_active:
                st.session_state.message = (
                    "success",
                    f"⏹️ Stopped {model_repo} (general cronjob still running for other models)",
                )
            else:
                st.session_state.message = (
                    "success",
                    f"⏹️ Stopped {model_repo} and removed all cronjobs",
                )
        else:
            st.session_state.message = ("error", "Failed to stop")
    st.rerun()


# Display message if exists (after Control Panel)
if st.session_state.message:
    msg_type, msg_text = st.session_state.message
    if msg_type == "success":
        st.success(msg_text)
    elif msg_type == "error":
        st.error(msg_text)
    elif msg_type == "warning":
        st.warning(msg_text)
    elif msg_type == "info":
        st.info(msg_text)
    st.session_state.message = None  # Clear after displaying

st.markdown("---")

# Status table
st.markdown("### 🏃🏻 Status")

table_data = []
for model in AVAILABLE_MODELS:
    model_config = active_configs.get(model)

    if model_config:
        # Get status from config
        model_status = model_config.get("status", "running")
        if model_status == "running":
            status = "🟢 Running"
        elif model_status == "error":
            status = "⚠️ Error"
        else:
            status = "🔴 Stopped"

        target_url_display = model_config.get("target_url", "")
        # Format time displays (HH:MM only)
        from_time_display = ":".join(model_config.get("from_time", "").split(":")[:2])
        to_time_display = ":".join(model_config.get("to_time", "").split(":")[:2])
        interval_display = f"{model_config.get('interval_minutes', 0)} min"

        # Format started time
        started_time = model_config.get("last_updated", "")
        if started_time:
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(started_time.replace("Z", "+00:00"))
                started_display = dt.strftime("%y/%m/%d %H:%M:%S")
            except (ValueError, AttributeError):
                started_display = (
                    started_time[:19] if len(started_time) >= 19 else started_time
                )
        else:
            started_display = ""
    else:
        status = "🔴 Stopped"
        target_url_display = ""
        from_time_display = ""
        to_time_display = ""
        interval_display = ""
        started_display = ""

    table_data.append(
        {
            "Model": model,
            "Status": status,
            "URL": target_url_display,
            "From": from_time_display,
            "To": to_time_display,
            "Interval": interval_display,
            "Started": started_display,
        }
    )

df = pd.DataFrame(table_data)
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Model": st.column_config.TextColumn("Model", width="medium"),
        "Status": st.column_config.TextColumn("Status", width="small"),
        "URL": st.column_config.TextColumn(
            "URL", width="large"
        ),  # Make URL column larger
        "From": st.column_config.TextColumn("From", width="small"),
        "To": st.column_config.TextColumn("To", width="small"),
        "Interval": st.column_config.TextColumn("Interval", width="small"),
        "Started": st.column_config.TextColumn("Started", width="medium"),
    },
)
