import sqlite3
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from .backup_db import backup_folder, copy_database

REQUIRED_TABLES = {"lounge_product", "lounge_order", "lounge_reservation", "django_migrations"}


class Command(BaseCommand):
    help = (
        "Replace the current database with a backup file. Stop the development server first. "
        "The current database is copied to the backup folder before it is replaced."
    )

    def add_arguments(self, parser):
        parser.add_argument("backup", help="Path to a .sqlite3 file created by backup_db")
        parser.add_argument("--yes", action="store_true", help="Don't ask for confirmation")

    def handle(self, *args, backup, yes=False, **options):
        source = Path(backup)
        if not source.is_file():
            raise CommandError(f"{source} doesn't exist.")
        check = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        try:
            integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        except sqlite3.DatabaseError as exc:
            raise CommandError(f"{source} isn't a readable SQLite database: {exc}") from exc
        finally:
            check.close()
        if integrity != "ok":
            raise CommandError(f"{source} failed its integrity check: {integrity}")
        missing = REQUIRED_TABLES - tables
        if missing:
            raise CommandError(f"{source} doesn't look like a ZenLeaf database (missing {', '.join(sorted(missing))}).")

        if not yes:
            answer = input(f"Replace the current database with {source}? Stop the server first. Type 'yes' to continue: ")
            if answer.strip().lower() != "yes":
                raise CommandError("Restore cancelled; nothing changed.")

        connection.ensure_connection()
        live = connection.connection
        folder = backup_folder()
        folder.mkdir(parents=True, exist_ok=True)
        safety = folder / f"before-restore-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        copy_database(live, safety)
        self.stdout.write(f"Saved the current database to {safety}")

        src = sqlite3.connect(source)
        try:
            src.backup(live)
        finally:
            src.close()
        connection.close()
        self.stdout.write(self.style.SUCCESS(f"Restored {source}. Start the server again to use it."))
