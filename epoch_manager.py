"""
Epoch manager — called by GitHub Actions daily.
1. Reads current epoch number from challenges/current.json
2. Archives the current challenge to challenges/epoch-N.json
3. Generates a new challenge via Gemini
4. Writes new challenge to challenges/current.json
5. Resets submissions.json for the new epoch
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from generator import issue_challenge

CHALLENGES_DIR = Path("challenges")
CURRENT = CHALLENGES_DIR / "current.json"
SUBMISSIONS = Path("submissions.json")


def load_current() -> dict:
    if CURRENT.exists():
        return json.loads(CURRENT.read_text())
    return {"epoch": 0}


def archive_current(challenge: dict) -> None:
    epoch = challenge.get("epoch", 0)
    archive_path = CHALLENGES_DIR / f"epoch-{epoch}.json"
    archive_path.write_text(json.dumps(challenge, indent=2))
    print(f"  archived → {archive_path}")


def reset_submissions(new_epoch: int) -> None:
    data = {
        "submissions": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "epoch": new_epoch,
    }
    SUBMISSIONS.write_text(json.dumps(data, indent=2))
    print(f"  submissions.json reset for epoch {new_epoch}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", default="math", choices=["math", "logic", "code"])
    args = parser.parse_args()

    print(f"\n── YUKA Epoch Manager ──────────────────────")

    current = load_current()
    prev_epoch = current.get("epoch", 0)
    new_epoch = prev_epoch + 1

    print(f"  previous epoch: {prev_epoch}")
    print(f"  new epoch:      {new_epoch}")
    print(f"  challenge type: {args.type}")

    # Archive old challenge
    if CURRENT.exists():
        archive_current(current)

    # Generate new challenge
    print(f"\n  generating new challenge...")
    CHALLENGES_DIR.mkdir(exist_ok=True)
    new_challenge = issue_challenge(challenge_type=args.type, epoch=new_epoch)

    # Write to current.json
    CURRENT.write_text(json.dumps(new_challenge, indent=2))
    print(f"  wrote → {CURRENT}")
    print(f"  hash:   {new_challenge['answer_hash'][:24]}...")

    # Reset submissions for new epoch
    reset_submissions(new_epoch)

    print(f"\n  ✓ epoch {new_epoch} ready")
    print(f"  closes: {new_challenge['expires_at']}")
    print(f"──────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
