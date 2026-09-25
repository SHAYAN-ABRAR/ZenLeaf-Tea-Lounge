"""Build the online demo: a browser-only edition of the site for static hosting such as GitHub Pages.

GitHub Pages serves files; it can't run Django or keep a database. This command renders the site's
templates in "demo mode" into plain HTML files and copies the static files next to them. In the
browser, lounge/static/lounge/js/demo.js then fills in the menu, cart, orders, table requests,
messages and staff pages from data kept in the visitor's own browser (localStorage).

It needs no database: the demo menu comes from lounge/seed_data.py.

    python manage.py build_demo --output _site --base-path /ZenLeaf-Tea-Lounge/
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.contrib.staticfiles.finders import get_finders
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import set_script_prefix

from lounge.forms import (
    CheckoutForm, ContactForm, OrderUpdateForm, ProductForm, ReservationForm, ReservationUpdateForm,
    format_time, reservation_slots,
)
from lounge.illustrations import ILLUSTRATIONS, PHOTOS
from lounge.models import ContactMessage, Order, Product, Reservation
from lounge.seed_data import CATEGORIES, PRODUCTS
from lounge.templatetags.lounge_tags import ICONS, STATUS_TONES
from lounge.views.staff import MESSAGE_FILTERS, ORDER_FILTERS, PRODUCT_STATES, RESERVATION_STATUSES, RESERVATION_WHEN

MARKER = ".zenleaf-demo-build"


def demo_categories():
    return [SimpleNamespace(slug=slug, name=name, description=description, sort_order=order)
            for slug, name, description, order in CATEGORIES]


def demo_products():
    products = []
    for pk, (slug, cat, name, short, description, price, illustration, caffeine, temperature, brew_time,
             notes, allergens, available, featured, order) in enumerate(PRODUCTS, start=1):
        products.append({
            "id": pk, "slug": slug, "category": cat, "name": name, "short_description": short,
            "description": description, "price": float(price), "illustration": illustration,
            "caffeine": caffeine, "brew_temperature_c": temperature, "brew_time": brew_time,
            "tasting_notes": notes, "allergens": allergens, "is_listed": True, "is_available": available,
            "is_featured": featured, "sort_order": order,
        })
    return products


def product_form(**kwargs):
    """The staff product form, with category choices keyed by slug (the demo has no database ids)."""
    form = ProductForm(**kwargs)
    form.fields["category"].widget.choices = [("", "Choose a category")] + [(c.slug, c.name) for c in demo_categories()]
    return form


def pages():
    """(output path, template, extra context) for every page of the demo."""
    categories = demo_categories()
    conf = settings.ZENLEAF
    hours = {   # as in the reserve view
        "opening": format_time(datetime.strptime(conf["OPENING_TIME"], "%H:%M").time()),
        "last": format_time(datetime.strptime(conf["LAST_SEATING"], "%H:%M").time()),
    }
    staff_lists = {
        "states": [(key, label) for key, (label, _q) in PRODUCT_STATES.items()],
        "filters_orders": [(key, label) for key, (label, _q) in ORDER_FILTERS.items()],
        "filters_messages": [(key, label) for key, (label, _q) in MESSAGE_FILTERS.items()],
    }
    return [
        ("", "demo/home.html", {"nav": "home", "max_party": conf["MAX_PARTY_SIZE"]}),
        ("menu/", "demo/menu.html", {"nav": "menu", "categories": categories}),
        ("menu/item/", "demo/product.html", {"nav": "menu"}),
        ("cart/", "demo/cart.html", {"nav": "cart"}),
        ("checkout/", "demo/checkout.html", {"nav": "cart", "form": CheckoutForm()}),
        ("orders/", "demo/order.html", {}),
        ("reserve/", "demo/reserve.html", {"nav": "reserve", "form": ReservationForm(), "hours": hours}),
        ("reservations/", "demo/reservation.html", {}),
        ("contact/", "demo/contact.html", {"nav": "contact", "form": ContactForm(initial={"topic": "general"})}),
        ("about/", "demo/about.html", {"nav": "about"}),
        ("404.html", "demo/404.html", {}),
        ("staff/", "demo/staff/dashboard.html", {"section": "dashboard"}),
        ("staff/products/", "demo/staff/products.html",
         {"section": "products", "states": staff_lists["states"], "categories": categories}),
        ("staff/products/new/", "demo/staff/product_form.html",
         {"section": "products", "form": product_form(initial={"is_listed": True, "is_available": True})}),
        ("staff/products/edit/", "demo/staff/product_form.html",
         {"section": "products", "form": product_form(), "editing": True}),
        ("staff/products/delete/", "demo/staff/product_delete.html", {"section": "products"}),
        ("staff/orders/", "demo/staff/orders.html", {"section": "orders", "filters": staff_lists["filters_orders"]}),
        ("staff/orders/view/", "demo/staff/order.html", {"section": "orders", "form": OrderUpdateForm()}),
        ("staff/reservations/", "demo/staff/reservations.html", {
            "section": "reservations", "statuses": list(RESERVATION_STATUSES.items()),
            "whens": list(RESERVATION_WHEN.items()),
        }),
        ("staff/reservations/view/", "demo/staff/reservation.html",
         {"section": "reservations", "form": ReservationUpdateForm()}),
        ("staff/messages/", "demo/staff/messages.html",
         {"section": "messages", "filters": staff_lists["filters_messages"]}),
        ("staff/messages/view/", "demo/staff/message.html", {"section": "messages"}),
        ("staff/subscribers/", "demo/staff/subscribers.html", {"section": "subscribers"}),
    ]


def demo_data(base):
    """Everything demo.js needs, from the same sources the Django site uses."""
    conf = settings.ZENLEAF
    return {
        "version": 1,
        "base": base,
        "static": f"{base}static/lounge/",
        "settings": {
            "currency_symbol": conf["CURRENCY_SYMBOL"],
            "max_party_size": conf["MAX_PARTY_SIZE"],
            "booking_days_ahead": conf["BOOKING_DAYS_AHEAD"],
            "min_notice_minutes": conf["MIN_NOTICE_MINUTES"],
            "max_item_quantity": conf["MAX_ITEM_QUANTITY"],
            "slots": [slot.strftime("%H:%M") for slot in reservation_slots()],
        },
        "categories": [vars(c) for c in demo_categories()],
        "products": demo_products(),
        "illustrations": {key: {"label": label, "alt": alt} for key, (label, alt) in ILLUSTRATIONS.items()},
        "photos": dict(PHOTOS),   # key -> alt text, for the keys that have a photo
        "icons": ICONS,
        "labels": {
            "caffeine": dict(Product.Caffeine.choices),
            "order_status": dict(Order.Status.choices),
            "order_progress": [str(status) for status in Order.PROGRESS],
            "reservation_status": dict(Reservation.Status.choices),
            "topics": dict(ContactMessage.Topic.choices),
            "tones": STATUS_TONES,
        },
    }


class Command(BaseCommand):
    help = "Build the browser-only online demo (for GitHub Pages) into a folder of static files."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="_site", help="Folder to write (default: _site). It is replaced.")
        parser.add_argument("--base-path", default="/",
                            help="URL path the site is served from, for example /ZenLeaf-Tea-Lounge/ on GitHub Pages.")

    def handle(self, *args, output, base_path, **options):
        base = "/" + base_path.strip("/") + "/" if base_path.strip("/") else "/"
        out = Path(output).resolve()
        if out.exists():
            if any(out.iterdir()) and not (out / MARKER).exists():
                raise CommandError(f"{out} isn't empty and wasn't made by build_demo, so it wasn't replaced.")
            shutil.rmtree(out)
        out.mkdir(parents=True)
        (out / MARKER).write_text("Made by `python manage.py build_demo`; safe to delete.\n", encoding="utf-8")

        factory = RequestFactory()
        written = 0
        # Links and static URLs must include the base path, e.g. /ZenLeaf-Tea-Lounge/menu/.
        with override_settings(STATIC_URL=f"{base}static/"):
            set_script_prefix(base)
            try:
                for path, template, extra in pages():
                    request = factory.get(base + ("" if path.endswith(".html") else path))
                    # "NOTPROVIDED" keeps {% csrf_token %} from writing a token into static files.
                    context = {"demo": True, "csrf_token": "NOTPROVIDED", **extra}
                    html = render_to_string(template, context, request=request)
                    target = out / path if path.endswith(".html") else out / path / "index.html"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(html, encoding="utf-8")
                    written += 1
            finally:
                set_script_prefix("/")

        copied = 0
        for finder in get_finders():
            for relative, storage in finder.list([]):
                target = out / "static" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with storage.open(relative) as source, open(target, "wb") as destination:
                    shutil.copyfileobj(source, destination)
                copied += 1

        data = json.dumps(demo_data(base), ensure_ascii=False, separators=(",", ":"))
        (out / "static" / "lounge" / "js" / "demo-data.js").write_text(
            "/* Generated by `python manage.py build_demo`. */\nwindow.ZENLEAF_DEMO = " + data + ";\n", encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(
            f"Built the online demo in {out}: {written} pages and {copied} static files, served from {base}"))
