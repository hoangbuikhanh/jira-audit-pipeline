import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.config import Config
from src.jira_reader import (
    fetch_todo_tasks,
    fetch_stale_in_progress,
    parse_issue,
    days_since,
)


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


SAMPLE_ISSUE = {
    "key": "TEST-1",
    "fields": {
        "summary": "Fix login bug",
        "assignee": {"displayName": "John Doe"},
        "priority": {"name": "High"},
        "created": "2026-03-01T10:00:00+00:00",
        "updated": "2026-03-05T10:00:00+00:00",
    },
}


class TestParseIssue(unittest.TestCase):
    def test_parse_full_issue(self):
        result = parse_issue(SAMPLE_ISSUE)
        self.assertEqual(result["key"], "TEST-1")
        self.assertEqual(result["summary"], "Fix login bug")
        self.assertEqual(result["assignee"], "John Doe")
        self.assertEqual(result["priority"], "High")

    def test_parse_unassigned_issue(self):
        issue = {
            "key": "TEST-2",
            "fields": {
                "summary": "Task",
                "assignee": None,
                "priority": None,
                "created": "",
                "updated": "",
            },
        }
        result = parse_issue(issue)
        self.assertEqual(result["assignee"], "Unassigned")
        self.assertEqual(result["priority"], "None")


class TestDaysSince(unittest.TestCase):
    def test_days_since_recent(self):
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.assertEqual(days_since(yesterday), 1)

    def test_days_since_empty(self):
        self.assertEqual(days_since(""), 0)

    def test_days_since_z_suffix(self):
        five_days_ago = (datetime.now(timezone.utc) - timedelta(days=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self.assertEqual(days_since(five_days_ago), 5)


class TestFetchTasks(unittest.TestCase):
    @patch("src.jira_reader.requests.get")
    def test_fetch_todo_tasks(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "issues": [SAMPLE_ISSUE],
            "total": 1,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        config = _make_config()
        result = fetch_todo_tasks(config)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["key"], "TEST-1")
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("To Do", call_args.kwargs["params"]["jql"])

    @patch("src.jira_reader.requests.get")
    def test_fetch_stale_in_progress(self, mock_get):
        issue_with_changelog = {
            **SAMPLE_ISSUE,
            "changelog": {
                "histories": [{
                    "created": "2026-01-01T10:00:00+00:00",
                    "items": [{"field": "status", "toString": "In Progress"}],
                }],
            },
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "issues": [issue_with_changelog],
            "total": 1,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        config = _make_config()
        result = fetch_stale_in_progress(config)

        self.assertEqual(len(result), 1)
        call_args = mock_get.call_args
        self.assertIn("In Progress", call_args.kwargs["params"]["jql"])
        self.assertEqual(call_args.kwargs["params"]["expand"], "changelog")

    @patch("src.jira_reader.requests.get")
    def test_fetch_stale_in_progress_excludes_recent(self, mock_get):
        from datetime import timedelta
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        issue_recent = {
            **SAMPLE_ISSUE,
            "changelog": {
                "histories": [{
                    "created": yesterday,
                    "items": [{"field": "status", "toString": "In Progress"}],
                }],
            },
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"issues": [issue_recent], "total": 1}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        config = _make_config()
        result = fetch_stale_in_progress(config)
        self.assertEqual(len(result), 0)

    @patch("src.jira_reader.requests.get")
    def test_pagination(self, mock_get):
        page1 = MagicMock()
        page1.json.return_value = {"issues": [SAMPLE_ISSUE], "total": 101}
        page1.raise_for_status = MagicMock()

        page2 = MagicMock()
        page2.json.return_value = {"issues": [SAMPLE_ISSUE], "total": 101}
        page2.raise_for_status = MagicMock()

        mock_get.side_effect = [page1, page2]

        config = _make_config()
        result = fetch_todo_tasks(config)
        self.assertEqual(len(result), 2)
        self.assertEqual(mock_get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
