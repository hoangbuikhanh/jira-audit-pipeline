import unittest
from unittest.mock import patch, MagicMock

from src.config import Config
from src.audit_logic import AuditReport, run_audit


def _make_config() -> Config:
    return Config(
        jira_base_url="https://test.atlassian.net",
        jira_email="test@test.com",
        jira_api_token="token",
        jira_project_key="TEST",
        google_chat_webhook_url="https://chat.test",
        in_progress_threshold_days=3,
        jira_team_label="",
        jira_active_sprint_only=False,
    )


SAMPLE_TODO = {
    "key": "TEST-1",
    "fields": {
        "summary": "Implement feature",
        "assignee": {"displayName": "Alice"},
        "priority": {"name": "Medium"},
        "created": "2026-03-01T10:00:00+00:00",
        "updated": "2026-03-01T10:00:00+00:00",
    },
}

SAMPLE_STALE = {
    "key": "TEST-2",
    "fields": {
        "summary": "Stuck task",
        "assignee": {"displayName": "Bob"},
        "priority": {"name": "High"},
        "created": "2026-02-20T10:00:00+00:00",
        "updated": "2026-02-25T10:00:00+00:00",
    },
}


class TestAuditReport(unittest.TestCase):
    def test_empty_report(self):
        report = AuditReport(project_key="TEST")
        self.assertFalse(report.has_warnings)
        self.assertEqual(report.total_warnings, 0)

    @patch("src.audit_logic.fetch_stale_in_progress")
    @patch("src.audit_logic.fetch_todo_tasks")
    def test_run_audit_with_results(self, mock_todo, mock_stale):
        mock_todo.return_value = [SAMPLE_TODO]
        mock_stale.return_value = [SAMPLE_STALE]

        config = _make_config()
        report = run_audit(config)

        self.assertEqual(len(report.todo_items), 1)
        self.assertEqual(len(report.stale_items), 1)
        self.assertTrue(report.has_warnings)
        self.assertEqual(report.total_warnings, 2)
        self.assertEqual(report.todo_items[0].key, "TEST-1")
        self.assertEqual(report.todo_items[0].category, "todo")
        self.assertEqual(report.stale_items[0].key, "TEST-2")
        self.assertEqual(report.stale_items[0].category, "stale_in_progress")

    @patch("src.audit_logic.fetch_stale_in_progress")
    @patch("src.audit_logic.fetch_todo_tasks")
    def test_run_audit_empty(self, mock_todo, mock_stale):
        mock_todo.return_value = []
        mock_stale.return_value = []

        config = _make_config()
        report = run_audit(config)

        self.assertFalse(report.has_warnings)
        self.assertEqual(report.total_warnings, 0)


if __name__ == "__main__":
    unittest.main()
