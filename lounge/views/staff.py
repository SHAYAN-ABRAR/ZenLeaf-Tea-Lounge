import csv
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from ..forms import OrderUpdateForm, ProductForm, ReservationUpdateForm, StaffLoginForm, format_time
from ..illustrations import ILLUSTRATIONS
from ..models import Category, ContactMessage, NewsletterSubscriber, Order, Product, Reservation
from .public import safe_next, wants_json

PAGE_SIZE = 25


def staff_required(view):
    """Anonymous visitors go to the login page; signed-in accounts without staff access get a 403."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("staff:login"))
        if not (request.user.is_active and request.user.is_staff):
            raise PermissionDenied("Staff access only.")
        return view(request, *args, **kwargs)
    return wrapper


class StaffLoginView(LoginView):
    template_name = "staff/login.html"
    authentication_form = StaffLoginForm
    redirect_authenticated_user = True


class StaffLogoutView(LogoutView):
    next_page = "staff:login"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "You're signed out.")
        return response


def paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))


@staff_required
def dashboard(request):
    today = timezone.localdate()
    context = {
        "section": "dashboard",
        "counts": {
            "open_orders": Order.objects.filter(status__in=["received", "preparing", "ready"]).count(),
            "new_orders": Order.objects.filter(status="received").count(),
            "pending_reservations": Reservation.objects.filter(status="pending", date__gte=today).count(),
            "today_reservations": Reservation.objects.filter(date=today, status__in=["pending", "confirmed"]).count(),
            "new_messages": ContactMessage.objects.filter(is_handled=False).count(),
            "sold_out": Product.objects.filter(is_listed=True, is_available=False).count(),
        },
        "recent_orders": Order.objects.all()[:5],
        "pending_reservations": Reservation.objects.filter(status="pending", date__gte=today)[:5],
    }
    return render(request, "staff/dashboard.html", context)


# --- Products ----------------------------------------------------------------------------------------

PRODUCT_STATES = {
    "all": ("All", Q()),
    "listed": ("On the menu", Q(is_listed=True)),
    "sold-out": ("Sold out", Q(is_listed=True, is_available=False)),
    "hidden": ("Hidden", Q(is_listed=False)),
    "featured": ("Featured", Q(is_featured=True)),
}


@staff_required
def product_list(request):
    query = request.GET.get("q", "").strip()[:60]
    state = request.GET.get("state", "all")
    state = state if state in PRODUCT_STATES else "all"
    category = request.GET.get("category", "")
    products = Product.objects.select_related("category").filter(PRODUCT_STATES[state][1])
    if query:
        products = products.filter(Q(name__icontains=query) | Q(short_description__icontains=query))
    if category:
        products = products.filter(category__slug=category)
    return render(request, "staff/product_list.html", {
        "section": "products", "page": paginate(request, products), "query": query, "state": state,
        "states": [(key, label) for key, (label, _q) in PRODUCT_STATES.items()],
        "categories": Category.objects.all(), "category": category,
    })


TOGGLE_FIELDS = {
    "is_available": ("available to order", "sold out"),
    "is_listed": ("shown on the menu", "hidden from the menu"),
    "is_featured": ("featured", "not featured"),
}


@staff_required
@require_POST
def product_toggle(request, pk, field):
    if field not in TOGGLE_FIELDS:
        return JsonResponse({"ok": False, "message": "Unknown setting."}, status=400)
    product = get_object_or_404(Product, pk=pk)
    setattr(product, field, not getattr(product, field))
    product.save(update_fields=[field, "updated_at"])
    on, off = TOGGLE_FIELDS[field]
    text = f"{product.name} is now {on if getattr(product, field) else off}."
    if wants_json(request):
        return JsonResponse({"ok": True, "value": getattr(product, field), "message": text})
    messages.success(request, text)
    return redirect(safe_next(request, reverse("staff:products")))


@staff_required
@require_http_methods(["GET", "POST"])
def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f"Saved {saved.name}.")
            return redirect("staff:products")
    else:
        form = ProductForm(instance=product, initial=None if product else {"is_listed": True, "is_available": True})
    return render(request, "staff/product_form.html", {
        "section": "products", "form": form, "product": product,
        "illustrations": ILLUSTRATIONS,
    })


@staff_required
@require_http_methods(["GET", "POST"])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    ordered = product.order_items.count()
    if request.method == "POST":
        name = product.name
        try:
            product.delete()
        except ProtectedError:
            messages.error(request, f"{name} couldn't be deleted.")
            return redirect("staff:product_edit", pk=pk)
        messages.success(request, f"Deleted {name}. Past orders keep its name and price.")
        return redirect("staff:products")
    return render(request, "staff/product_delete.html", {"section": "products", "product": product, "ordered": ordered})


# --- Orders ---------------------------------------------------------------------------------------------

ORDER_FILTERS = {
    "open": ("Open", Q(status__in=["received", "preparing", "ready"])),
    "received": ("Received", Q(status="received")),
    "preparing": ("Being prepared", Q(status="preparing")),
    "ready": ("Ready", Q(status="ready")),
    "completed": ("Collected", Q(status="completed")),
    "cancelled": ("Cancelled", Q(status="cancelled")),
    "all": ("All", Q()),
}


@staff_required
def order_list(request):
    status = request.GET.get("status", "open")
    status = status if status in ORDER_FILTERS else "open"
    query = request.GET.get("q", "").strip()[:60]
    orders = Order.objects.filter(ORDER_FILTERS[status][1])
    if query:
        orders = orders.filter(Q(number__icontains=query) | Q(customer_name__icontains=query) | Q(email__icontains=query))
    return render(request, "staff/order_list.html", {
        "section": "orders", "page": paginate(request, orders), "status": status, "query": query,
        "filters": [(key, label) for key, (label, _q) in ORDER_FILTERS.items()],
    })


@staff_required
@require_http_methods(["GET", "POST"])
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    if request.method == "POST":
        form = OrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f"Order {order.number} updated: {order.get_status_display()}.")
            return redirect("staff:order_detail", pk=order.pk)
    else:
        form = OrderUpdateForm(instance=order)
    return render(request, "staff/order_detail.html", {"section": "orders", "order": order, "form": form})


# --- Reservations -----------------------------------------------------------------------------------------

RESERVATION_STATUSES = {"pending": "Pending", "confirmed": "Confirmed", "declined": "Declined",
                        "cancelled": "Cancelled", "all": "All"}
RESERVATION_WHEN = {"upcoming": "Upcoming", "past": "Past", "all": "Any date"}


@staff_required
def reservation_list(request):
    status = request.GET.get("status", "pending")
    status = status if status in RESERVATION_STATUSES else "pending"
    when = request.GET.get("when", "upcoming")
    when = when if when in RESERVATION_WHEN else "upcoming"
    today = timezone.localdate()
    reservations = Reservation.objects.all()
    if status != "all":
        reservations = reservations.filter(status=status)
    if when == "upcoming":
        reservations = reservations.filter(date__gte=today)
    elif when == "past":
        reservations = reservations.filter(date__lt=today).order_by("-date", "-time")
    return render(request, "staff/reservation_list.html", {
        "section": "reservations", "page": paginate(request, reservations), "status": status, "when": when,
        "statuses": list(RESERVATION_STATUSES.items()), "whens": list(RESERVATION_WHEN.items()),
    })


@staff_required
@require_http_methods(["GET", "POST"])
def reservation_detail(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.method == "POST":
        form = ReservationUpdateForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            messages.success(request, f"Request {reservation.reference} updated: {reservation.get_status_display()}.")
            return redirect("staff:reservation_detail", pk=reservation.pk)
    else:
        form = ReservationUpdateForm(instance=reservation)
    return render(request, "staff/reservation_detail.html", {
        "section": "reservations", "reservation": reservation, "form": form,
        "time_label": format_time(reservation.time),
    })


# --- Messages and subscribers -----------------------------------------------------------------------------

MESSAGE_FILTERS = {"new": ("To handle", Q(is_handled=False)), "handled": ("Handled", Q(is_handled=True)), "all": ("All", Q())}


@staff_required
def message_list(request):
    state = request.GET.get("state", "new")
    state = state if state in MESSAGE_FILTERS else "new"
    return render(request, "staff/message_list.html", {
        "section": "messages", "page": paginate(request, ContactMessage.objects.filter(MESSAGE_FILTERS[state][1])),
        "state": state, "filters": [(key, label) for key, (label, _q) in MESSAGE_FILTERS.items()],
    })


@staff_required
def message_detail(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    if message.read_at is None:
        message.read_at = timezone.now()
        message.save(update_fields=["read_at"])
    return render(request, "staff/message_detail.html", {"section": "messages", "item": message})


@staff_required
@require_POST
def message_toggle(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    message.is_handled = not message.is_handled
    message.save(update_fields=["is_handled"])
    messages.success(request, "Marked as handled." if message.is_handled else "Moved back to the to-handle list.")
    return redirect("staff:message_detail", pk=pk)


@staff_required
def subscriber_list(request):
    return render(request, "staff/subscriber_list.html", {
        "section": "subscribers", "page": paginate(request, NewsletterSubscriber.objects.all()),
        "total": NewsletterSubscriber.objects.count(),
    })


@staff_required
def subscriber_export(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="zenleaf-subscribers-{timezone.localdate():%Y%m%d}.csv"'
    writer = csv.writer(response)
    writer.writerow(["email", "source", "subscribed_at"])
    for sub in NewsletterSubscriber.objects.order_by("created_at"):
        writer.writerow([sub.email, sub.source, timezone.localtime(sub.created_at).isoformat(timespec="minutes")])
    return response


@staff_required
@require_POST
def subscriber_delete(request, pk):
    subscriber = get_object_or_404(NewsletterSubscriber, pk=pk)
    subscriber.delete()
    messages.success(request, f"Removed {subscriber.email} from the list.")
    return redirect("staff:subscribers")
