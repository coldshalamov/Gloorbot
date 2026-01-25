#!/usr/bin/env python3
"""
Force task reseed on gloorbot-coordinator to fix store clustering issue.
This script deletes all tasks and triggers a reseed with the new category-major ordering.
"""
import os
import sys
from pathlib import Path

# Add coordinator app to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "coordinator"))

from coordinator_app.db import db_session
from coordinator_app.models import Task
from coordinator_app.seed import seed_tasks_from_parallel_urls
from sqlalchemy import delete

def main():
    print("🔄 Forcing task reseed to fix store clustering...")

    repo_root = Path(__file__).parent

    with db_session() as db:
        # Delete ALL tasks
        count = db.execute(delete(Task)).rowcount
        db.commit()
        print(f"✅ Deleted {count} old tasks")

    # Reseed with category-major ordering
    inserted = seed_tasks_from_parallel_urls(repo_root)
    print(f"✅ Inserted {inserted} new tasks in category-major order")

    print("\n🎉 Done! Tasks are now interleaved across stores.")
    print("   Your worker's 5 slots will now spread across different stores.")

if __name__ == "__main__":
    main()
