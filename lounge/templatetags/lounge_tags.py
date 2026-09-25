from decimal import ROUND_HALF_UP, Decimal

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..illustrations import PHOTOS, photo_path

register = template.Library()

# Line icons drawn for this project on a 24 × 24 grid. They inherit the text color.
ICONS = {
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    "bag": '<path d="M5.5 8.5h13l-1.2 11.5H6.7L5.5 8.5z"/><path d="M9 8.5V7a3 3 0 0 1 6 0v1.5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7"/>',
    "alert": '<path d="M12 4l9 16H3L12 4z"/><path d="M12 10v4M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "calendar": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.2c2.6.4 4.5 2.6 4.5 5.8"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4.5 20c0-4 3.4-7 7.5-7s7.5 3 7.5 7"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5L12 13l8.5-6.5"/>',
    "leaf": '<path d="M5 19c0-8 6-14 14-14 0 8-6 14-14 14z"/><path d="M5 19l9-9"/>',
    "thermometer": '<path d="M10 4.5a2 2 0 0 1 4 0v9.3a4 4 0 1 1-4 0V4.5z"/><path d="M12 9v7.5"/>',
    "timer": '<circle cx="12" cy="13.5" r="7"/><path d="M12 10v3.5l2.5 1.5M10 3h4"/>',
    "bolt": '<path d="M13 3L5.5 13.5h5.5L10 21l7.5-10.5H12L13 3z"/>',
    "arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "trash": '<path d="M5 7h14M10 11v6M14 11v6M6.5 7l1 13h9l1-13M9.5 7V4h5v3"/>',
    "logout": '<path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "cup": '<path d="M5 9h11v4.5a5.5 5.5 0 0 1-5.5 5.5 5.5 5.5 0 0 1-5.5-5.5V9z"/><path d="M16 10.5h1.5a2.5 2.5 0 0 1 0 5H16M8.5 3.5c-.8.9.8 1.6 0 2.5M12 3.5c-.8.9.8 1.6 0 2.5"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01"/>',
    "download": '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>',
    "eye-off": '<path d="M4 4l16 16M10.6 6.1A9.8 9.8 0 0 1 12 6c5 0 8.5 4.6 9.5 6-.5.8-1.6 2.2-3.1 3.5M6.1 7.9C4.3 9.1 3 10.9 2.5 12c1 1.4 4.5 6 9.5 6 1.4 0 2.7-.4 3.9-.9M9.9 10a3 3 0 0 0 4.1 4.1"/>',
}


@register.simple_tag
def icon(name, extra_class=""):
    body = ICONS.get(name)
    if body is None:
        return ""
    cls = f"icon {extra_class}".strip()
    return format_html(
        '<svg class="{}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{}</svg>',
        cls, mark_safe(body),
    )


@register.simple_tag
def render_field(bound_field, **attrs):
    """Render a form widget with the ARIA attributes that tie it to its hint and error text."""
    extra = {key.replace("_", "-"): value for key, value in attrs.items()}
    described = []
    if bound_field.help_text:
        described.append(f"{bound_field.auto_id}-hint")
    if bound_field.errors:
        described.append(f"{bound_field.auto_id}-error")
        extra["aria-invalid"] = "true"
    if described:
        extra["aria-describedby"] = " ".join(described)
    return bound_field.as_widget(attrs=extra)


@register.filter
def money(value):
    """220 -> '৳ 220', 1234.5 -> '৳ 1,234.50' (currency symbol from settings)."""
    if value in (None, ""):
        return ""
    amount = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    text = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    return f"{settings.ZENLEAF['CURRENCY_SYMBOL']}\u202f{text}"   # narrow no-break space


@register.filter
def clock(value):
    """A time or datetime as '6:30 pm', in the site's time zone (Django's own 'a' format gives 'p.m.')."""
    from datetime import datetime

    from django.utils import timezone

    from ..forms import format_time

    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        value = timezone.localtime(value).time() if timezone.is_aware(value) else value.time()
    return format_time(value)


@register.simple_tag(takes_context=True)
def query_with(context, **changes):
    """Current query string with some parameters replaced (None or '' removes them)."""
    params = context["request"].GET.copy()
    for key, value in changes.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"


STATUS_TONES = {
    "received": "info", "preparing": "warning", "ready": "success", "completed": "neutral",
    "cancelled": "neutral", "pending": "warning", "confirmed": "success", "declined": "danger",
}


@register.filter
def status_tone(status):
    return STATUS_TONES.get(status, "neutral")


@register.filter
def picture_preview(key):
    """URL of the small picture for a product picture key: its 480 px photo, or its drawing if it has no photo."""
    if not key:
        return ""
    return static(photo_path(key, 480) or f"lounge/img/menu/{key}.svg")


@register.simple_tag
def photo_keys():
    """The picture keys that have a photo, separated by spaces (read by the staff picture preview)."""
    return " ".join(PHOTOS)
