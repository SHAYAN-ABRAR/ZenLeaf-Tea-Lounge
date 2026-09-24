"""A small .env reader, so settings can come from a local file without an extra dependency.

Each line looks like KEY=value. Blank lines and lines starting with # are ignored, and a value may
be wrapped in single or double quotes. Inline comments after a value are not supported. Variables
that already exist in the real environment always win, so a hosting platform can override the file.
"""
import os
from pathlib import Path

TRUE_VALUES = {"1", "true", "yes", "on"}


def load_env_file(path):
    """Copy KEY=value pairs from *path* into os.environ (without overriding). Returns True if read."""
    path = Path(path)
    if not path.is_file():
        return False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)
    return True


def env_str(name, default=""):
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in TRUE_VALUES


def env_int(name, default):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def env_list(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]
