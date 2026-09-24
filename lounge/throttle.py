"""Count failed staff logins per (IP address, username) and lock that pair out for a while.

The counts live in Django's cache (process memory by default), which is enough for one local
server. A multi-server deployment would need a shared cache such as Redis for this to hold."""
import hashlib

from django.conf import settings
from django.core.cache import cache


def key_for(request, username):
    ip = (request.META.get("REMOTE_ADDR") or "unknown") if request is not None else "unknown"
    digest = hashlib.sha256(f"{ip}|{username.strip().lower()}".encode()).hexdigest()
    return f"login-fail:{digest}"


def is_locked(key):
    return cache.get(key, 0) >= settings.LOGIN_MAX_ATTEMPTS


def record_failure(key):
    timeout = settings.LOGIN_LOCKOUT_MINUTES * 60
    if cache.add(key, 1, timeout):
        return 1
    try:
        return cache.incr(key)
    except ValueError:  # expired between add() and incr()
        cache.set(key, 1, timeout)
        return 1


def reset(key):
    cache.delete(key)
