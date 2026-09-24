from django.conf import settings
from django.utils import timezone

from .cart import Cart
from .forms import NewsletterForm


def site(request):
    """Values every public page needs: the cart count for the header and the footer sign-up form."""
    cart_count = len(Cart(request)) if hasattr(request, "session") else 0
    return {
        "cart_count": cart_count,
        "footer_newsletter_form": NewsletterForm(auto_id="newsletter-%s"),
        "current_year": timezone.localdate().year,
        "max_party": settings.ZENLEAF["MAX_PARTY_SIZE"],
    }


def staff(request):
    """Counts for the staff navigation. Only runs on staff pages, and only for signed-in staff."""
    match = getattr(request, "resolver_match", None)
    if match is None or match.namespace != "staff":
        return {}
    from .models import ContactMessage, Order, Reservation

    context = {"login_max_attempts": settings.LOGIN_MAX_ATTEMPTS, "login_lockout_minutes": settings.LOGIN_LOCKOUT_MINUTES}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.is_staff:
        context["staff_counts"] = {
            "orders": Order.objects.filter(status=Order.Status.RECEIVED).count(),
            "reservations": Reservation.objects.filter(
                status=Reservation.Status.PENDING, date__gte=timezone.localdate()).count(),
            "messages": ContactMessage.objects.filter(is_handled=False).count(),
        }
    return context
