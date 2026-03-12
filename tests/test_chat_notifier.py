import json
import unittest
from io import StringIO
from unittest.mock import patch, MagicMock

from src.audit_logic import AuditItem, AuditReport
from src.chat_notifier import build_card_payload, send_to_google_chat


def _make_report() -> AuditReport:
    report = AuditReport(project_key="TEST", threshold_days=3)
    report.todo_items = [
        AuditItem(
            key="TEST-1",
            summary="Fix bug",
            assignee="Alice",
            priority="High",
            days_old=5,
            category="todo",
        ),
    ]
    report.stale_items = [
        AuditItem(
            key="TEST-2",
            summary="Stuck task",
            assignee="Bob",
            priority="Medium",
            days_old=7,
            category="stale_in_progress",
        ),
    ]
    return report


class TestBuildCardPayload(unittest.TestCase):
    def test_builds_valid_payload(self):
        report = _make_report()
        payload = build_card_payload(report)

        self.assertIn("cardsV2", payload)
        card = payload["cardsV2"][0]["card"]
        self.assertEqual(card["header"]["title"], "Jira Audit: TEST")
        self.assertIn("2 warning(s)", card["header"]["subtitle"])
        self.assertEqual(len(card["sections"]), 2)

    def test_empty_report_no_sections(self):
        report = AuditReport(project_key="TEST")
        payload = build_card_payload(report)
        card = payload["cardsV2"][0]["card"]
        self.assertEqual(len(card["sections"]), 0)

    def test_only_todo_section(self):
        report = _make_report()
        report.stale_items = []
        payload = build_card_payload(report)
        card = payload["cardsV2"][0]["card"]
        self.assertEqual(len(card["sections"]), 1)
        self.assertIn("To Do", card["sections"][0]["header"])


class TestSendToGoogleChat(unittest.TestCase):
    def test_dry_run_prints_payload(self):
        report = _make_report()
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = send_to_google_chat("https://fake", report, dry_run=True)
            self.assertTrue(result)
            output = mock_stdout.getvalue()
            data = json.loads(output)
            self.assertIn("cardsV2", data)

    @patch("src.chat_notifier.requests.post")
    def test_send_real_request(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        report = _make_report()
        result = send_to_google_chat("https://chat.test/webhook", report)
        self.assertTrue(result)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs.args[0], "https://chat.test/webhook")


if __name__ == "__main__":
    unittest.main()
