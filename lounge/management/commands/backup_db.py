import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


def backup_folder():
    folder = Path(settings.ZENLEAF["BACKUP_DIR"])
    return folder if folder.is_absolute() else settings.BASE_DIR / folder


def copy_database(live, target):
    """Copy an open SQLite connection into *target* and return the copy's integrity-check result.
    The copy is switched to a plain rollback journal so it stays a single self-contained file."""
    copy = sqlite3.connect(target)
    try:
        live.backup(copy)
        copy.execute("PRAGMA journal_mode=DELETE")
        return copy.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        copy.close()


class Command(BaseCommand):
    help = (
        "Copy the SQLite database to a timestamped file with SQLite's online backup API. "
        "It is safe to run while the site is running."
    )

    def add_arguments(self, parser):
        parser.add_argument("--output", help="File to write (default: backups/zenleaf-YYYYmmdd-HHMMSS.sqlite3)")
        parser.add_argument("--keep", type=int, default=0,
                            help="After backing up, keep only this many newest backups in the backup folder.")

    def handle(self, *args, output=None, keep=0, **options):
        if connection.vendor != "sqlite":
            raise CommandError("backup_db only works with the SQLite database this project uses.")
        folder = backup_folder()
        target = Path(output) if output else folder / f"zenleaf-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        if target.exists():
            raise CommandError(f"{target} already exists; choose another --output.")
        target.parent.mkdir(parents=True, exist_ok=True)

        # Copy through Django's own connection, so the backup is of exactly the database the site uses.
        connection.ensure_connection()
        result = copy_database(connection.connection, target)
        if result != "ok":
            raise CommandError(f"The backup failed its integrity check: {result}")
        self.stdout.write(self.style.SUCCESS(f"Backed up the database to {target} ({target.stat().st_size // 1024} KB)."))

        if keep and not output:
            for old in sorted(folder.glob("zenleaf-*.sqlite3"))[:-keep]:
                for path in (old, old.with_name(old.name + "-wal"), old.with_name(old.name + "-shm")):
                    path.unlink(missing_ok=True)
                self.stdout.write(f"Removed old backup {old.name}")
