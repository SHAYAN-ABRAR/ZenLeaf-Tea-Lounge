#!/usr/bin/env python3
"""Set up, or refresh, a local copy of ZenLeaf Tea Lounge. It is safe to run again at any time.

    python bootstrap.py               # virtual environment, packages, .env, database, demo menu
    python bootstrap.py --reset-menu  # the same, and restore the demo menu to its original values

It never deletes the database and never overwrites an existing .env file.
"""
import argparse
import os
import secrets
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PLACEHOLDER = "DJANGO_SECRET_KEY=change-me-to-a-long-random-string"


def venv_python():
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(args, **kwargs):
    root = str(ROOT) + os.sep
    shown = [str(a)[len(root):] if str(a).startswith(root) else str(a) for a in args]
    print("  $", " ".join(shown))
    return subprocess.run([str(a) for a in args], cwd=ROOT, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset-menu", action="store_true", help="restore the demo products to their seed values")
    args = parser.parse_args()

    if sys.version_info < (3, 10):
        sys.exit(f"Python 3.10 or newer is needed (this is {sys.version.split()[0]}). Install a newer Python and run this again.")

    print("1/5  Virtual environment (.venv)")
    if venv_python().exists():
        print("  already there")
    else:
        try:
            venv.create(VENV, with_pip=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            sys.exit(f"Couldn't create the virtual environment ({exc}).\n"
                     "On Debian or Ubuntu, install it with `sudo apt install python3-venv`, then run this again.")
        print("  created")
    py = venv_python()

    print("2/5  Packages from requirements.txt")
    run([py, "-m", "pip", "install", "--disable-pip-version-check", "--quiet", "-r", "requirements.txt"])

    print("3/5  Settings (.env)")
    env_file = ROOT / ".env"
    if env_file.exists():
        print("  .env already exists, so it was left unchanged")
    else:
        template = (ROOT / ".env.example").read_text(encoding="utf-8")
        env_file.write_text(template.replace(PLACEHOLDER, "DJANGO_SECRET_KEY=" + secrets.token_urlsafe(50)), encoding="utf-8")
        print("  created .env from .env.example, with a new random secret key")

    print("4/5  Database migrations")
    run([py, "manage.py", "migrate", "--noinput"])

    print("5/5  Demo menu")
    run([py, "manage.py", "seed_demo"] + (["--reset"] if args.reset_menu else []))

    count_staff = ("import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zenleaf.settings'); django.setup(); "
                   "from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(is_staff=True).count())")
    check = subprocess.run([str(py), "-c", count_staff], cwd=ROOT, check=True, capture_output=True, text=True)
    staff_accounts = int(check.stdout.strip().splitlines()[-1])
    run_cmd = r".venv\Scripts\python manage.py" if os.name == "nt" else ".venv/bin/python manage.py"

    print("\nSetup complete.")
    if staff_accounts == 0:
        print("\nNo staff account exists yet. Create one for the staff area (you choose the password):")
        print(f"  {run_cmd} createsuperuser")
        if sys.stdin.isatty():
            answer = input("\nCreate it now? [Y/n] ").strip().lower()
            if answer in ("", "y", "yes"):
                run([py, "manage.py", "createsuperuser"])
    print("\nStart the site with:")
    print(f"  {run_cmd} runserver")
    print("Then open http://127.0.0.1:8000/ (staff area: http://127.0.0.1:8000/staff/).")


if __name__ == "__main__":
    main()
