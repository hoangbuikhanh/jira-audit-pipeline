import argparse
import sys

from src.audit_logic import run_audit
from src.chat_notifier import send_to_google_chat
from src.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Jira Audit Pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print payload to terminal instead of sending",
    )
    args = parser.parse_args()

    try:
        config = load_config()
        report = run_audit(config)

        if not report.has_warnings:
            print(f"No warnings for project {config.jira_project_key}.")
            return 0

        print(
            f"Found {report.total_warnings} warning(s): "
            f"{len(report.todo_items)} todo, "
            f"{len(report.stale_items)} stale in-progress"
        )

        send_to_google_chat(
            config.google_chat_webhook_url, report, dry_run=args.dry_run
        )

        if not args.dry_run:
            print("Report sent to Google Chat.")

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
