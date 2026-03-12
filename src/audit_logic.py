from dataclasses import dataclass, field

from src.config import Config
from src.jira_reader import (
    days_since,
    fetch_stale_in_progress,
    fetch_todo_tasks,
    parse_issue,
)


@dataclass
class AuditItem:
    key: str
    summary: str
    assignee: str
    priority: str
    days_old: int
    category: str  # "todo" | "stale_in_progress"


@dataclass
class AuditReport:
    project_key: str
    todo_items: list[AuditItem] = field(default_factory=list)
    stale_items: list[AuditItem] = field(default_factory=list)
    threshold_days: int = 3

    @property
    def total_warnings(self) -> int:
        return len(self.todo_items) + len(self.stale_items)

    @property
    def has_warnings(self) -> bool:
        return self.total_warnings > 0


def run_audit(config: Config) -> AuditReport:
    report = AuditReport(
        project_key=config.jira_project_key,
        threshold_days=config.in_progress_threshold_days,
    )

    todo_issues = fetch_todo_tasks(config)
    for issue in todo_issues:
        parsed = parse_issue(issue)
        report.todo_items.append(
            AuditItem(
                key=parsed["key"],
                summary=parsed["summary"],
                assignee=parsed["assignee"],
                priority=parsed["priority"],
                days_old=days_since(parsed["created"]),
                category="todo",
            )
        )

    stale_issues = fetch_stale_in_progress(config)
    for issue in stale_issues:
        parsed = parse_issue(issue)
        report.stale_items.append(
            AuditItem(
                key=parsed["key"],
                summary=parsed["summary"],
                assignee=parsed["assignee"],
                priority=parsed["priority"],
                days_old=days_since(parsed["in_progress_since"]),
                category="stale_in_progress",
            )
        )

    return report
