#!/usr/bin/env python3
"""
SAM Brain Approval CLI
View and approve/reject pending destructive operations.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

APPROVAL_QUEUE = Path("/Volumes/Plex/SSOT/pending_approvals.json")


def load_queue():
    """Load the approval queue."""
    if APPROVAL_QUEUE.exists():
        with open(APPROVAL_QUEUE) as f:
            return json.load(f)
    return []


def save_queue(queue):
    """Save the approval queue."""
    with open(APPROVAL_QUEUE, "w") as f:
        json.dump(queue, f, indent=2)


def list_pending():
    """List all pending approvals."""
    queue = load_queue()
    pending = [a for a in queue if a.get("status") == "pending"]

    if not pending:
        print("\n✓ No pending approvals\n")
        return

    print("\n" + "=" * 60)
    print("  PENDING APPROVALS")
    print("=" * 60 + "\n")

    for i, item in enumerate(pending, 1):
        print(f"[{i}] {item.get('project')} - {item.get('action')}")
        print(f"    Command: {item.get('command')}")
        print(f"    Reason: {item.get('reason')}")
        print(f"    Time: {item.get('timestamp')}")
        print()


def approve(item_id: str):
    """Approve a pending item."""
    queue = load_queue()

    for item in queue:
        if item.get("id") == item_id or item.get("project") == item_id:
            if item.get("status") == "pending":
                item["status"] = "approved"
                item["approved_at"] = datetime.now().isoformat()
                save_queue(queue)
                print(f"✓ Approved: {item.get('action')} for {item.get('project')}")
                return

    print(f"Item not found or already processed: {item_id}")


def reject(item_id: str):
    """Reject a pending item."""
    queue = load_queue()

    for item in queue:
        if item.get("id") == item_id or item.get("project") == item_id:
            if item.get("status") == "pending":
                item["status"] = "rejected"
                item["rejected_at"] = datetime.now().isoformat()
                save_queue(queue)
                print(f"✗ Rejected: {item.get('action')} for {item.get('project')}")
                return

    print(f"Item not found or already processed: {item_id}")


def approve_all():
    """Approve all pending items."""
    queue = load_queue()
    count = 0

    for item in queue:
        if item.get("status") == "pending":
            item["status"] = "approved"
            item["approved_at"] = datetime.now().isoformat()
            count += 1

    save_queue(queue)
    print(f"✓ Approved {count} items")


def reject_all():
    """Reject all pending items."""
    queue = load_queue()
    count = 0

    for item in queue:
        if item.get("status") == "pending":
            item["status"] = "rejected"
            item["rejected_at"] = datetime.now().isoformat()
            count += 1

    save_queue(queue)
    print(f"✗ Rejected {count} items")


def clear_processed():
    """Remove all approved/rejected items."""
    queue = load_queue()
    pending = [a for a in queue if a.get("status") == "pending"]
    removed = len(queue) - len(pending)
    save_queue(pending)
    print(f"Cleared {removed} processed items")


def main():
    if len(sys.argv) < 2:
        print("\nSAM Brain Approval CLI")
        print("=" * 40)
        print("\nUsage:")
        print("  approval_cli.py list           - List pending approvals")
        print("  approval_cli.py approve <id>   - Approve an item")
        print("  approval_cli.py reject <id>    - Reject an item")
        print("  approval_cli.py approve-all    - Approve all pending")
        print("  approval_cli.py reject-all     - Reject all pending")
        print("  approval_cli.py clear          - Clear processed items")
        print()
        list_pending()
        return

    cmd = sys.argv[1].lower()

    if cmd == "list":
        list_pending()
    elif cmd == "approve" and len(sys.argv) > 2:
        approve(sys.argv[2])
    elif cmd == "reject" and len(sys.argv) > 2:
        reject(sys.argv[2])
    elif cmd == "approve-all":
        approve_all()
    elif cmd == "reject-all":
        reject_all()
    elif cmd == "clear":
        clear_processed()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
