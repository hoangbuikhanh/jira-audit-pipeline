from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

from src.config import Config


def _auth(config: Config) -> HTTPBasicAuth:
    return HTTPBasicAuth(config.jira_email, config.jira_api_token)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _search_issues(config: Config, jql: str, fields: str) -> list[dict[str, Any]]:
    url = f"{config.jira_base_url}/rest/api/2/search"
    session = _session()
    issues: list[dict[str, Any]] = []
    start_at = 0
    max_results = 100

    while True:
        resp = session.get(
            url,
            auth=_auth(config),
            params={
                "jql": jql,
                "fields": fields,
                "startAt": start_at,
                "maxResults": max_results,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data.get("issues", []))

        total = data.get("total", 0)
        start_at += max_results
        if start_at >= total:
            break

    return issues


def _build_base_jql(config: Config) -> str:
    jql = f'project = "{config.jira_project_key}"'
    jql += " AND issuetype not in subTaskIssueTypes()"
    if config.jira_team_label:
        jql += f' AND labels = "{config.jira_team_label}"'
    if config.jira_active_sprint_only:
        jql += " AND sprint in openSprints()"
    return jql


def fetch_todo_tasks(config: Config) -> list[dict[str, Any]]:
    jql = (
        f'{_build_base_jql(config)} '
        f'AND status = "To Do" '
        f"ORDER BY created ASC"
    )
    return _search_issues(config, jql, "summary,assignee,priority,created")


def _search_issues_with_changelog(config: Config, jql: str, fields: str) -> list[dict[str, Any]]:
    url = f"{config.jira_base_url}/rest/api/2/search"
    session = _session()
    issues: list[dict[str, Any]] = []
    start_at = 0
    max_results = 100

    while True:
        resp = session.get(
            url,
            auth=_auth(config),
            params={
                "jql": jql,
                "fields": fields,
                "startAt": start_at,
                "maxResults": max_results,
                "expand": "changelog",
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data.get("issues", []))

        total = data.get("total", 0)
        start_at += max_results
        if start_at >= total:
            break

    return issues


def _get_in_progress_since(issue: dict[str, Any]) -> str:
    changelog = issue.get("changelog", {})
    histories = changelog.get("histories", [])
    last_transition = ""
    for history in histories:
        for item in history.get("items", []):
            if item.get("field") == "status" and item.get("toString") == "In Progress":
                last_transition = history.get("created", "")
    return last_transition


def fetch_stale_in_progress(config: Config) -> list[dict[str, Any]]:
    jql = (
        f'{_build_base_jql(config)} '
        f'AND status = "In Progress" '
        f"ORDER BY updated ASC"
    )
    all_issues = _search_issues_with_changelog(
        config, jql, "summary,assignee,priority,updated"
    )

    threshold = config.in_progress_threshold_days
    stale = []
    for issue in all_issues:
        since = _get_in_progress_since(issue)
        if since and days_since(since) >= threshold:
            issue["_in_progress_since"] = since
            stale.append(issue)

    return stale


def parse_issue(issue: dict[str, Any]) -> dict[str, str]:
    fields = issue.get("fields", {})
    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
    priority = fields.get("priority")
    priority_name = priority.get("name", "None") if priority else "None"

    return {
        "key": issue.get("key", ""),
        "summary": fields.get("summary", ""),
        "assignee": assignee_name,
        "priority": priority_name,
        "created": fields.get("created", ""),
        "updated": fields.get("updated", ""),
        "in_progress_since": issue.get("_in_progress_since", ""),
    }


def _parse_jira_date(iso_date: str) -> datetime:
    """Parse Jira date strings like '2025-02-27T16:21:51.000+0100'."""
    import re
    # Fix timezone offset: +0100 -> +01:00 (needed for Python 3.9)
    fixed = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', iso_date)
    fixed = fixed.replace("Z", "+00:00")
    return datetime.fromisoformat(fixed)


def days_since(iso_date: str) -> int:
    if not iso_date:
        return 0
    dt = _parse_jira_date(iso_date)
    now = datetime.now(timezone.utc)
    return (now - dt).days
