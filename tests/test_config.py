import os
import unittest
from unittest.mock import patch

from src.config import load_config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.env = {
            "JIRA_BASE_URL": "https://test.atlassian.net",
            "JIRA_EMAIL": "test@test.com",
            "JIRA_API_TOKEN": "token123",
            "JIRA_PROJECT_KEY": "TEST",
            "GOOGLE_CHAT_WEBHOOK_URL": "https://chat.googleapis.com/test",
        }

    def test_load_config_success(self):
        with unittest.mock.patch.dict(os.environ, self.env, clear=False):
            config = load_config()
            self.assertEqual(config.jira_base_url, "https://test.atlassian.net")
            self.assertEqual(config.jira_email, "test@test.com")
            self.assertEqual(config.jira_project_key, "TEST")
            self.assertEqual(config.in_progress_threshold_days, 3)

    def test_load_config_strips_trailing_slash(self):
        self.env["JIRA_BASE_URL"] = "https://test.atlassian.net/"
        with unittest.mock.patch.dict(os.environ, self.env, clear=False):
            config = load_config()
            self.assertEqual(config.jira_base_url, "https://test.atlassian.net")

    def test_load_config_custom_threshold(self):
        self.env["IN_PROGRESS_THRESHOLD_DAYS"] = "7"
        with unittest.mock.patch.dict(os.environ, self.env, clear=False):
            config = load_config()
            self.assertEqual(config.in_progress_threshold_days, 7)

    @patch("src.config.load_dotenv")
    def test_load_config_missing_required(self, mock_dotenv):
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                load_config()
            self.assertIn("JIRA_BASE_URL", str(ctx.exception))

    def test_invalid_project_key_rejected(self):
        self.env["JIRA_PROJECT_KEY"] = "invalid-key"
        with unittest.mock.patch.dict(os.environ, self.env, clear=False):
            with self.assertRaises(ValueError) as ctx:
                load_config()
            self.assertIn("Invalid JIRA_PROJECT_KEY", str(ctx.exception))

    def test_zero_threshold_rejected(self):
        self.env["IN_PROGRESS_THRESHOLD_DAYS"] = "0"
        with unittest.mock.patch.dict(os.environ, self.env, clear=False):
            with self.assertRaises(ValueError) as ctx:
                load_config()
            self.assertIn("must be >= 1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
