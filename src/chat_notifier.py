import html
import json

import requests

from src.audit_logic import AuditItem, AuditReport


def _build_issue_row(item: AuditItem) -> str:
    summary = html.escape(item.summary)
    assignee = html.escape(item.assignee)
    return f"<b>{item.key}</b> — {summary}  [{assignee}] ({item.days_old}d)"


def build_card_payload(report: AuditReport) -> dict:
    sections = []

    if report.todo_items:
        lines = [_build_issue_row(item) for item in report.todo_items]
        sections.append({
            "header": f"To Do — {len(report.todo_items)} tasks",
            "widgets": [{"textParagraph": {"text": "<br>".join(lines)}}],
        })

    if report.stale_items:
        lines = [_build_issue_row(item) for item in report.stale_items]
        sections.append({
            "header": f"Stale In Progress (>{report.threshold_days}d) — {len(report.stale_items)} tasks",
            "widgets": [{"textParagraph": {"text": "<br>".join(lines)}}],
        })

    return {
        "cardsV2": [{
            "cardId": "jira-audit",
            "card": {
                "header": {
                    "title": f"Jira Audit: {report.project_key}",
                    "subtitle": f"{report.total_warnings} warning(s)",
                },
                "sections": sections,
            },
        }],
    }


def send_to_google_chat(webhook_url: str, report: AuditReport, dry_run: bool = False) -> bool:
    payload = build_card_payload(report)

    if dry_run:
        print(json.dumps(payload, indent=2))
        return True

    resp = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        timeout=15,
    )
    resp.raise_for_status()
    return True
