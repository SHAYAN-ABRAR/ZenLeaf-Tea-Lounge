from datetime import datetime, timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.text import slugify

from . import throttle
from .illustrations import ILLUSTRATION_CHOICES
from .models import ContactMessage, Order, Product, Reservation

phone_validator = RegexValidator(
    r"^[0-9+()\-\s]{6,20}$",
    "Enter a phone number using digits, spaces, +, - or brackets (6 to 20 characters).",
)


def format_time(value):
    """10:00 -> '10:00 am' (portable; strftime's %-I doesn't work on Windows)."""
    hour = value.hour % 12 or 12
    return f"{hour}:{value.minute:02d} {'am' if value.hour < 12 else 'pm'}"


def reservation_slots():
    conf = settings.ZENLEAF
    start = datetime.strptime(conf["OPENING_TIME"], "%H:%M")
    end = datetime.strptime(conf["LAST_SEATING"], "%H:%M")
    slots, current = [], start
    while current <= end:
        slots.append(current.time())
        current += timedelta(minutes=conf["SLOT_MINUTES"])
    return slots


class HoneypotForm(forms.Form):
    """A field people never see. Automated spam tends to fill it; submissions that do are dropped."""
    website = forms.CharField(
        required=False, label="Leave this field empty",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    def is_spam(self):
        return bool(self.cleaned_data.get("website"))


class CheckoutForm(HoneypotForm):
    customer_name = forms.CharField(
        label="Name", max_length=80, error_messages={"required": "Enter your name."},
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email", max_length=254,
        error_messages={"required": "Enter your email address.", "invalid": "Enter a valid email address, like name@example.com."},
        help_text="Only used to identify your order in this demo; no emails are sent.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    phone = forms.CharField(
        label="Phone", max_length=20, required=False, validators=[phone_validator],
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
    )
    notes = forms.CharField(
        label="Notes for the counter", max_length=500, required=False,
        help_text="For example: less sweet, milk on the side.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class ReservationForm(HoneypotForm):
    date = forms.DateField(
        label="Date", widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={"required": "Choose a date.", "invalid": "Enter a date like 2026-10-05."},
    )
    time = forms.TypedChoiceField(
        label="Time", coerce=lambda v: datetime.strptime(v, "%H:%M").time(),
        error_messages={"required": "Choose a time.", "invalid_choice": "Choose one of the listed times."},
    )
    party_size = forms.TypedChoiceField(
        label="Party size", coerce=int,
        error_messages={"required": "Choose a party size.", "invalid_choice": "Choose one of the listed party sizes."},
    )
    name = forms.CharField(
        label="Name", max_length=80, error_messages={"required": "Enter your name."},
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email", max_length=254,
        error_messages={"required": "Enter your email address.", "invalid": "Enter a valid email address, like name@example.com."},
        help_text="Used to identify your request. This demo doesn't send emails.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    phone = forms.CharField(
        label="Phone", max_length=20, required=False, validators=[phone_validator],
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
    )
    notes = forms.CharField(
        label="Anything we should know?", max_length=300, required=False,
        help_text="For example: a high chair, a quiet table, a birthday.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        conf = settings.ZENLEAF
        today = timezone.localdate()
        self.fields["date"].widget.attrs.update({
            "min": today.isoformat(),
            "max": (today + timedelta(days=conf["BOOKING_DAYS_AHEAD"])).isoformat(),
        })
        self.fields["time"].choices = [("", "Choose a time")] + [
            (slot.strftime("%H:%M"), format_time(slot)) for slot in reservation_slots()
        ]
        self.fields["party_size"].choices = [("", "Choose")] + [
            (str(n), f"{n} {'person' if n == 1 else 'people'}") for n in range(1, conf["MAX_PARTY_SIZE"] + 1)
        ]

    def clean_date(self):
        value = self.cleaned_data["date"]
        today = timezone.localdate()
        days = settings.ZENLEAF["BOOKING_DAYS_AHEAD"]
        if value < today:
            raise forms.ValidationError("Choose today or a later date.")
        if value > today + timedelta(days=days):
            raise forms.ValidationError(f"Requests can be made up to {days} days ahead.")
        return value

    def clean(self):
        cleaned = super().clean()
        day, slot = cleaned.get("date"), cleaned.get("time")
        if day and slot and day == timezone.localdate():
            notice = settings.ZENLEAF["MIN_NOTICE_MINUTES"]
            earliest = timezone.localtime() + timedelta(minutes=notice)
            requested = timezone.make_aware(datetime.combine(day, slot))
            if requested < earliest:
                self.add_error("time", f"For today, choose a time at least {notice} minutes from now.")
        return cleaned


class ContactForm(HoneypotForm):
    name = forms.CharField(
        label="Name", max_length=80, error_messages={"required": "Enter your name."},
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email", max_length=254,
        error_messages={"required": "Enter your email address.", "invalid": "Enter a valid email address, like name@example.com."},
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    topic = forms.ChoiceField(label="Topic", choices=ContactMessage.Topic.choices)
    message = forms.CharField(
        label="Message", min_length=10, max_length=2000,
        widget=forms.Textarea(attrs={"rows": 6}),
        error_messages={
            "required": "Write your message.",
            "min_length": "Write at least 10 characters so we know how to help.",
            "max_length": "Keep the message under 2,000 characters.",
        },
    )


class NewsletterForm(HoneypotForm):
    email = forms.EmailField(
        label="Email address", max_length=254,
        error_messages={"required": "Enter your email address.", "invalid": "Enter a valid email address, like name@example.com."},
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class StaffLoginForm(AuthenticationForm):
    """Django's login form plus a lockout after repeated failures (per username and IP address)."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "That username and password don't match a staff account.",
        "locked": "Too many failed attempts. Try again in %(minutes)s minutes.",
        "not_staff": "This account doesn't have access to the staff area.",
    }

    def clean(self):
        username = self.cleaned_data.get("username") or ""
        key = throttle.key_for(self.request, username)
        if throttle.is_locked(key):
            raise forms.ValidationError(
                self.error_messages["locked"], code="locked",
                params={"minutes": settings.LOGIN_LOCKOUT_MINUTES},
            )
        try:
            cleaned = super().clean()
        except forms.ValidationError:
            throttle.record_failure(key)
            raise
        if self.get_user() is not None:
            # Only a successful sign-in clears the count. (A post with an empty password reaches this
            # point without authenticating, and must not reset it.)
            throttle.reset(key)
        return cleaned

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(self.error_messages["not_staff"], code="not_staff")


class ProductForm(forms.ModelForm):
    slug = forms.SlugField(
        max_length=90, required=False,
        help_text="Used in the product's web address. Leave empty to create it from the name.",
    )

    class Meta:
        model = Product
        fields = [
            "name", "slug", "category", "short_description", "description", "price", "illustration",
            "caffeine", "brew_temperature_c", "brew_time", "tasting_notes", "allergens",
            "is_listed", "is_available", "is_featured", "sort_order",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "price": forms.NumberInput(attrs={"step": "1", "min": "1", "inputmode": "decimal"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = "Choose a category"
        self.fields["illustration"].choices = [("", "Choose a picture")] + ILLUSTRATION_CHOICES
        self.fields["illustration"].label = "Picture"
        self.fields["caffeine"].choices = [("", "Not applicable (food)")] + list(Product.Caffeine.choices)
        self.fields["sort_order"].label = "Sort order (lower comes first)"

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or slugify(self.cleaned_data.get("name", ""))
        if not slug:
            raise forms.ValidationError("Enter a name or a web address slug.")
        clash = Product.objects.filter(slug=slug).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("Another product already uses this slug.")
        return slug


class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "staff_note"]
        widgets = {"staff_note": forms.Textarea(attrs={"rows": 3})}


class ReservationUpdateForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ["status", "guest_message"]
        widgets = {"guest_message": forms.Textarea(attrs={"rows": 3})}
