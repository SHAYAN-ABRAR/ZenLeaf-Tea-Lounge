import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from ..cart import Cart
from ..forms import CheckoutForm, ContactForm, NewsletterForm, ReservationForm, format_time
from ..models import Category, ContactMessage, NewsletterSubscriber, Order, Product, Reservation

CHECKOUT_NONCE = "checkout_nonce"
LAST_ORDER = "last_order_token"


NEWSLETTER_SOURCES = {"footer"}


def wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch"


def parse_id(value):
    """A database id from form data: plain ASCII digits only ("²".isdigit() is True, for example)."""
    value = str(value or "")
    return int(value) if value.isascii() and value.isdigit() else None


def safe_next(request, fallback):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                   require_https=request.is_secure()):
        return target
    return fallback


# --- Pages ---------------------------------------------------------------------------------------

def home(request):
    featured = Product.objects.filter(is_listed=True, is_featured=True).select_related("category")[:4]
    # Aggregate queries ignore Meta.ordering, so the order is set explicitly.
    categories = (Category.objects.annotate(listed=Count("products", filter=Q(products__is_listed=True)))
                  .filter(listed__gt=0).order_by("sort_order", "name"))
    return render(request, "lounge/home.html", {"featured": featured, "categories": categories, "nav": "home"})


def menu(request):
    query = request.GET.get("q", "").strip()[:60]
    category_slug = request.GET.get("category", "").strip()
    available_only = request.GET.get("available") == "1"

    categories = list(Category.objects.filter(products__is_listed=True).distinct().order_by("sort_order", "name"))
    active_category = next((c for c in categories if c.slug == category_slug), None)

    products = Product.objects.filter(is_listed=True).select_related("category")
    if active_category:
        products = products.filter(category=active_category)
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(short_description__icontains=query)
            | Q(tasting_notes__icontains=query) | Q(category__name__icontains=query)
        )
    if available_only:
        products = products.filter(is_available=True)
    products = list(products)

    filtered = bool(query or active_category or available_only)
    groups = [] if filtered else [
        (category, [p for p in products if p.category_id == category.pk]) for category in categories
    ]
    return render(request, "lounge/menu.html", {
        "nav": "menu", "products": products, "groups": groups, "categories": categories,
        "active_category": active_category, "query": query, "available_only": available_only,
        "filtered": filtered, "unknown_category": bool(category_slug and not active_category),
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug, is_listed=True)
    related = (Product.objects.filter(category=product.category, is_listed=True)
               .exclude(pk=product.pk).select_related("category")[:3])
    return render(request, "lounge/product_detail.html", {
        "nav": "menu", "product": product, "related": related,
        "in_cart": Cart(request).quantity_of(product.pk),
    })


def about(request):
    return render(request, "lounge/about.html", {"nav": "about"})


# --- Cart ------------------------------------------------------------------------------------------

def cart_view(request):
    cart = Cart(request)
    lines = cart.lines()
    return render(request, "lounge/cart.html", {
        "nav": "cart", "lines": lines, "subtotal": Cart.subtotal(lines),
        "has_problems": any(line.problem for line in lines),
        "max_quantity": cart.max_quantity,
    })


@require_POST
def cart_add(request):
    cart = Cart(request)
    product_id = parse_id(request.POST.get("product_id"))
    product = Product.objects.filter(pk=product_id).first() if product_id is not None else None
    try:
        quantity = max(1, min(int(request.POST.get("quantity", 1)), cart.max_quantity))
    except (TypeError, ValueError):
        quantity = 1

    if product is None or not product.is_listed:
        return _cart_reply(request, cart, False, "That item isn't on the menu any more.", status=404)
    if not product.is_available:
        return _cart_reply(request, cart, False, f"Sorry, {product.name} is sold out right now.", status=409)

    before = cart.quantity_of(product.pk)
    after = cart.add(product, quantity)
    if after == before:
        text = f"You already have the maximum of {cart.max_quantity} × {product.name} in your cart."
        return _cart_reply(request, cart, False, text, status=409)
    return _cart_reply(request, cart, True, f"Added {product.name} to your cart.")


def _cart_reply(request, cart, ok, text, status=200):
    if wants_json(request):
        return JsonResponse({"ok": ok, "message": text, "count": len(cart), "cart_url": reverse("lounge:cart")},
                            status=200 if ok else status)
    (messages.success if ok else messages.error)(request, text)
    return redirect(safe_next(request, reverse("lounge:menu")))


@require_POST
def cart_update(request):
    cart = Cart(request)
    product_id = parse_id(request.POST.get("product_id"))
    raw_id = str(product_id)
    action = request.POST.get("action", "")
    if product_id is not None and action in {"increase", "decrease", "remove", "set"}:
        current = cart.quantity_of(raw_id)
        if action == "increase":
            cart.set(raw_id, current + 1)
        elif action == "decrease":
            cart.set(raw_id, current - 1)
        elif action == "remove":
            cart.remove(raw_id)
        else:
            try:
                cart.set(raw_id, int(request.POST.get("quantity", current)))
            except (TypeError, ValueError):
                messages.error(request, "Enter a whole number for the quantity.")
        if action == "remove" or cart.quantity_of(raw_id) == 0:
            messages.info(request, "Removed the item from your cart.")
    else:
        messages.error(request, "That cart update didn't work. Please try again.")
    return redirect("lounge:cart")


@require_http_methods(["GET", "POST"])
def checkout(request):
    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        if request.method == "POST" and request.session.get(LAST_ORDER):
            messages.info(request, "Your order was already placed.")
            return redirect("lounge:order_status", token=request.session[LAST_ORDER])
        messages.info(request, "Your cart is empty. Add something from the menu first.")
        return redirect("lounge:cart")
    if any(line.problem for line in lines):
        messages.error(request, "Some items in your cart can't be ordered right now. Remove them to continue.")
        return redirect("lounge:cart")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        expected = request.session.get(CHECKOUT_NONCE) or ""
        sent = request.POST.get("nonce", "")
        nonce_ok = bool(expected) and secrets.compare_digest(sent.encode(), expected.encode())
        if not nonce_ok:
            messages.error(request, "This checkout page expired. Please review your order and submit it again.")
            return redirect("lounge:checkout")
        if form.is_valid():
            data = form.cleaned_data
            nonce = request.session.pop(CHECKOUT_NONCE)
            if form.is_spam():
                cart.clear()
                return redirect("lounge:home")
            try:
                order = Order.place(
                    customer_name=data["customer_name"], email=data["email"], phone=data["phone"],
                    notes=data["notes"], lines=[(line.product, line.quantity) for line in lines],
                    checkout_key=nonce,
                )
            except IntegrityError:
                # The same checkout form was submitted twice at once; show the order that was saved.
                existing = Order.objects.filter(checkout_key=nonce).first()
                if existing is None:
                    raise
                cart.clear()
                return redirect(existing)
            cart.clear()
            request.session[LAST_ORDER] = order.token
            messages.success(request, f"Thank you, {order.customer_name.split()[0]}. Order {order.number} is saved.")
            return redirect(order)
    else:
        form = CheckoutForm()
    request.session[CHECKOUT_NONCE] = request.session.get(CHECKOUT_NONCE) or secrets.token_urlsafe(16)
    return render(request, "lounge/checkout.html", {
        "nav": "cart", "form": form, "lines": lines, "subtotal": Cart.subtotal(lines),
        "nonce": request.session[CHECKOUT_NONCE],
    })


def order_status(request, token):
    order = get_object_or_404(Order.objects.prefetch_related("items"), token=token)
    steps = [(value, label) for value, label in Order.Status.choices if value in Order.PROGRESS]
    return render(request, "lounge/order_status.html", {"order": order, "steps": steps})


# --- Reservations ------------------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def reserve(request):
    if request.method == "POST":
        form = ReservationForm(request.POST)
        if form.is_valid():
            if form.is_spam():
                return redirect("lounge:home")
            data = form.cleaned_data
            with transaction.atomic():
                reservation = Reservation.objects.create(
                    name=data["name"], email=data["email"], phone=data["phone"], date=data["date"],
                    time=data["time"], party_size=data["party_size"], notes=data["notes"],
                )
                reservation.assign_reference()
            messages.success(request, f"Request {reservation.reference} received. It's pending until a member of staff confirms it.")
            return redirect(reservation)
    else:
        initial = {}
        if request.GET.get("party", "").isdigit():
            initial["party_size"] = request.GET["party"]
        form = ReservationForm(initial=initial)
    conf = settings.ZENLEAF
    hours = {
        "opening": format_time(datetime.strptime(conf["OPENING_TIME"], "%H:%M").time()),
        "last": format_time(datetime.strptime(conf["LAST_SEATING"], "%H:%M").time()),
    }
    return render(request, "lounge/reserve.html", {"nav": "reserve", "form": form, "hours": hours})


def reservation_status(request, token):
    reservation = get_object_or_404(Reservation, token=token)
    return render(request, "lounge/reservation_status.html", {
        "reservation": reservation, "can_cancel": can_cancel(reservation),
        "time_label": format_time(reservation.time),
    })


def can_cancel(reservation):
    """Pending or confirmed requests can be cancelled until their start time."""
    starts = timezone.make_aware(datetime.combine(reservation.date, reservation.time))
    return reservation.is_active and starts > timezone.now()


@require_POST
def reservation_cancel(request, token):
    reservation = get_object_or_404(Reservation, token=token)
    if can_cancel(reservation):
        reservation.status = Reservation.Status.CANCELLED
        reservation.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Request {reservation.reference} is cancelled.")
    else:
        messages.info(request, "This request can't be cancelled any more, so nothing changed.")
    return redirect(reservation)


# --- Contact and newsletter ---------------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if form.is_spam():
                return redirect("lounge:contact")
            fingerprint = ContactMessage.make_fingerprint(data["email"], data["message"])
            recent = timezone.now() - timedelta(hours=24)
            if ContactMessage.objects.filter(fingerprint=fingerprint, created_at__gte=recent).exists():
                messages.info(request, "We already have this message from you, so it wasn't saved twice.")
            else:
                ContactMessage.objects.create(
                    name=data["name"], email=data["email"], topic=data["topic"],
                    message=data["message"], fingerprint=fingerprint,
                )
                messages.success(request, "Thanks, your message is saved. Staff can read it in the staff area.")
            return redirect("lounge:contact")
    else:
        form = ContactForm(initial={"topic": request.GET.get("topic", "general")})
    return render(request, "lounge/contact.html", {"nav": "contact", "form": form})


@require_POST
def newsletter_signup(request):
    form = NewsletterForm(request.POST)
    fallback = reverse("lounge:home")
    if not form.is_valid():
        error = form.errors.get("email", ["Enter a valid email address."])[0]
        return _newsletter_reply(request, False, error, fallback, status=400)
    if form.is_spam():
        return _newsletter_reply(request, True, "You're subscribed.", fallback)
    email = form.cleaned_data["email"]
    source = request.POST.get("source", "")
    if source not in NEWSLETTER_SOURCES:      # only known values; it ends up in the CSV export
        source = ""
    try:
        _obj, created = NewsletterSubscriber.objects.get_or_create(email=email, defaults={"source": source})
    except IntegrityError:
        created = False
    if created:
        return _newsletter_reply(request, True, "You're subscribed. This demo stores your address but never sends email.", fallback)
    return _newsletter_reply(request, True, "You're already subscribed with that address.", fallback, duplicate=True)


def _newsletter_reply(request, ok, text, fallback, status=200, duplicate=False):
    if wants_json(request):
        return JsonResponse({"ok": ok, "message": text, "duplicate": duplicate}, status=status if not ok else 200)
    if ok:
        (messages.info if duplicate else messages.success)(request, text)
    else:
        messages.error(request, f"Newsletter sign-up: {text}")
    return redirect(safe_next(request, fallback))


# --- Errors ---------------------------------------------------------------------------------------------

def page_not_found(request, exception):
    return render(request, "404.html", {"nav": ""}, status=404)


def server_error(request):
    # Rendered without the request context, so it works even if the database is unavailable.
    return HttpResponseServerError(loader.get_template("500.html").render())
