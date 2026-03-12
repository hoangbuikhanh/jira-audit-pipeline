import os
import re
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_project_key: str
    google_chat_webhook_url: str
    in_progress_threshold_days: int
    jira_team_label: str
    jira_active_sprint_only: bool


def load_config() -> Config:
    load_dotenv()

    required = [
        "JIRA_BASE_URL",
        "JIRA_EMAIL",
        "JIRA_API_TOKEN",
        "JIRA_PROJECT_KEY",
        "GOOGLE_CHAT_WEBHOOK_URL",
    ]

    missing = [var for var in required if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")

    project_key = os.getenv("JIRA_PROJECT_KEY", "")
    if not re.match(r"^[A-Z][A-Z0-9_]{1,19}$", project_key):
        raise ValueError(f"Invalid JIRA_PROJECT_KEY: {project_key!r}")

    threshold = int(os.getenv("IN_PROGRESS_THRESHOLD_DAYS", "3"))
    if threshold < 1:
        raise ValueError("IN_PROGRESS_THRESHOLD_DAYS must be >= 1")

    return Config(
        jira_base_url=os.getenv("JIRA_BASE_URL", "").rstrip("/"),
        jira_email=os.getenv("JIRA_EMAIL", ""),
        jira_api_token=os.getenv("JIRA_API_TOKEN", ""),
        jira_project_key=project_key,
        google_chat_webhook_url=os.getenv("GOOGLE_CHAT_WEBHOOK_URL", ""),
        in_progress_threshold_days=threshold,
        jira_team_label=os.getenv("JIRA_TEAM_LABEL", ""),
        jira_active_sprint_only=os.getenv("JIRA_ACTIVE_SPRINT_ONLY", "true").lower() == "true",
    )
