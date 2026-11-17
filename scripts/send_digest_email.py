import argparse

from copilot.digest import build_digest
from copilot.integrations.directory import Directory
from copilot.integrations.emailer import deliver, plan_emails
from copilot.store import Store


def main():
    parser = argparse.ArgumentParser(description="Generate and send meeting digest emails.")

    parser.add_argument(
        "meeting_id",
        help="Meeting ID, for example m001",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send emails through SMTP instead of creating .eml files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Resend emails even if their payload is unchanged.",
    )
    parser.add_argument(
        "--host",
        default="localhost",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1025,
    )
    parser.add_argument(
        "--sender",
        default="copilot@localhost",
    )

    args = parser.parse_args()

    store = Store()
    directory = Directory()

    digest = build_digest(
        store,
        args.meeting_id,
        directory,
    )

    plans = plan_emails(
        digest,
        directory,
    )

    print(f"\nMeeting: {digest.title}")
    print(f"Meeting ID: {digest.meeting_id}")
    print(f"Recipients: {len(plans)}")

    results = deliver(
        plans=plans,
        store=store,
        mid=args.meeting_id,
        sender=args.sender,
        send=args.send,
        force=args.force,
        host=args.host,
        port=args.port,
    )

    print("\n--- EMAIL RESULTS ---")

    for result in results:
        print(result)


if __name__ == "__main__":
    main()
