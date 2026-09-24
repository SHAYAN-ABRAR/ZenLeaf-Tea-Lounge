"""Customer flows through the real views: menu, cart, checkout, table requests, contact and newsletter."""
from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from lounge.models import ContactMessage, NewsletterSubscriber, Order, Product, Reservation
from lounge.views.public import server_error

from .utils import product, seed

FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}


class MenuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def names(self, **params):
        response = self.client.get(reverse("lounge:menu"), params)
        self.assertEqual(response.status_code, 200)
        return [p.name for p in response.context["products"]]

    def test_menu_shows_listed_items_only(self):
        Product.objects.filter(slug="matcha").update(is_listed=False)
        names = self.names()
        self.assertEqual(len(names), 20)
        self.assertNotIn("Matcha", names)
        self.assertEqual(self.client.get(reverse("lounge:product", args=["matcha"])).status_code, 404)

    def test_category_search_and_availability_filters(self):
        self.assertEqual(self.names(category="herbal"),
                         ["Chamomile", "Peppermint", "Rooibos vanilla", "Hibiscus & ginger"])
        self.assertEqual(self.names(q="malty"), ["Breakfast black"])
        self.assertNotIn("Hibiscus cooler", self.names(category="iced", available="1"))
        self.assertEqual(self.names(q="no-such-tea"), [])
        response = self.client.get(reverse("lounge:menu"), {"category": "nope"})
        self.assertContains(response, "That category isn't on the menu")

    def test_product_page_shows_price_and_sold_out_state(self):
        response = self.client.get(reverse("lounge:product", args=["hibiscus-cooler"]))
        self.assertContains(response, "210")
        self.assertContains(response, "sold out right now")
        self.assertNotContains(response, 'class="add-form')


class CartAndCheckoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def add(self, slug, quantity=1, **extra):
        return self.client.post(reverse("lounge:cart_add"), {"product_id": product(slug).pk, "quantity": quantity}, **extra)

    def update(self, slug, action, **data):
        return self.client.post(reverse("lounge:cart_update"), {"product_id": product(slug).pk, "action": action, **data})

    def cart(self):
        return self.client.session.get("cart", {})

    def checkout(self, **fields):
        page = self.client.get(reverse("lounge:checkout"))
        data = {"customer_name": "Test Guest", "email": "guest@example.com", "nonce": page.context["nonce"], **fields}
        return self.client.post(reverse("lounge:checkout"), data)

    def test_adding_and_changing_quantities(self):
        sencha = str(product("sencha").pk)
        self.assertRedirects(self.add("sencha", 2), reverse("lounge:menu"))
        self.assertEqual(self.cart(), {sencha: 2})
        self.update("sencha", "increase")
        self.update("sencha", "decrease")
        self.update("sencha", "decrease")
        self.assertEqual(self.cart(), {sencha: 1})
        self.update("sencha", "set", quantity=99)
        self.assertEqual(self.cart(), {sencha: 20})                 # capped at the maximum
        self.update("sencha", "remove")
        self.assertEqual(self.cart(), {})

    def test_add_answers_fetch_requests_with_json(self):
        response = self.add("matcha-latte", 2, **FETCH)
        self.assertEqual(response.json()["ok"], True)
        self.assertEqual(response.json()["count"], 2)
        sold_out = self.add("hibiscus-cooler", **FETCH)
        self.assertEqual((sold_out.status_code, sold_out.json()["ok"]), (409, False))
        self.assertEqual(self.client.post(reverse("lounge:cart_add"), {"product_id": 99999}, **FETCH).status_code, 404)

    def test_malformed_requests_are_refused_without_errors(self):
        self.assertEqual(self.client.post(reverse("lounge:cart_add"), {"product_id": "²"}, **FETCH).status_code, 404)
        self.client.post(reverse("lounge:cart_update"), {"product_id": "²", "action": "set", "quantity": "2"})
        self.assertEqual(self.cart(), {})
        self.assertEqual(self.client.get(reverse("lounge:cart")).status_code, 200)
        self.add("sencha")
        self.client.session.pop("checkout_nonce", None)
        forged = self.client.post(reverse("lounge:checkout"), {"customer_name": "A", "email": "a@example.com", "nonce": "-"})
        self.assertRedirects(forged, reverse("lounge:checkout"))
        self.assertFalse(Order.objects.exists())

    def test_checkout_with_an_empty_cart_goes_back_to_the_cart(self):
        self.assertRedirects(self.client.get(reverse("lounge:checkout")), reverse("lounge:cart"))

    def test_missing_details_are_reported_and_nothing_is_saved(self):
        self.add("sencha")
        response = self.checkout(customer_name="", email="not-an-email")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].errors,
                         {"customer_name": ["Enter your name."],
                          "email": ["Enter a valid email address, like name@example.com."]})
        self.assertFalse(Order.objects.exists())

    def test_order_is_saved_with_current_database_prices(self):
        self.add("sencha", 2)
        self.add("masala-chai")
        Product.objects.filter(slug="sencha").update(price=Decimal("250"))   # price changes after adding
        response = self.checkout(notes="Less sweet, please.")
        order = Order.objects.get()
        self.assertRedirects(response, order.get_absolute_url())
        self.assertEqual((order.number, order.subtotal, order.notes), ("ZL-00001", Decimal("680"), "Less sweet, please."))
        self.assertEqual(self.cart(), {})
        status_page = self.client.get(order.get_absolute_url())
        self.assertContains(status_page, "Order ZL-00001")
        self.assertContains(status_page, "Received")

    def test_submitting_the_same_checkout_twice_creates_one_order(self):
        self.add("sencha")
        page = self.client.get(reverse("lounge:checkout"))
        data = {"customer_name": "Test Guest", "email": "guest@example.com", "nonce": page.context["nonce"]}
        first = self.client.post(reverse("lounge:checkout"), data)
        second = self.client.post(reverse("lounge:checkout"), data)
        order = Order.objects.get()
        self.assertRedirects(first, order.get_absolute_url())
        self.assertRedirects(second, order.get_absolute_url())

    def test_sold_out_items_block_checkout(self):
        self.add("sencha")
        nonce = self.client.get(reverse("lounge:checkout")).context["nonce"]
        Product.objects.filter(slug="sencha").update(is_available=False)   # sold out while the guest checks out
        response = self.client.post(reverse("lounge:checkout"),
                                    {"customer_name": "Test Guest", "email": "guest@example.com", "nonce": nonce})
        self.assertRedirects(response, reverse("lounge:cart"))
        self.assertFalse(Order.objects.exists())
        self.assertContains(self.client.get(reverse("lounge:cart")), "sold out right now")

    def test_a_stale_checkout_page_is_not_accepted(self):
        self.add("sencha")
        self.client.get(reverse("lounge:checkout"))
        response = self.client.post(reverse("lounge:checkout"),
                                    {"customer_name": "Test Guest", "email": "guest@example.com", "nonce": "old"})
        self.assertRedirects(response, reverse("lounge:checkout"))
        self.assertFalse(Order.objects.exists())


# Fixed booking rules, so the tests don't depend on values someone set in .env.
BOOKING_RULES = {"OPENING_TIME": "10:00", "LAST_SEATING": "20:00", "SLOT_MINUTES": 30, "MAX_PARTY_SIZE": 8,
                 "BOOKING_DAYS_AHEAD": 60, "MIN_NOTICE_MINUTES": 60}


@override_settings(ZENLEAF={**settings.ZENLEAF, **BOOKING_RULES})
class ReservationTests(TestCase):
    def request_table(self, day, slot="18:00", party="3", **extra):
        data = {"date": day.isoformat(), "time": slot, "party_size": party, "name": "Test Guest",
                "email": "guest@example.com", **extra}
        return self.client.post(reverse("lounge:reserve"), data)

    def test_dates_must_be_between_today_and_the_booking_window(self):
        today = timezone.localdate()
        past = self.request_table(today - timedelta(days=1))
        self.assertEqual(past.context["form"].errors["date"], ["Choose today or a later date."])
        far = self.request_table(today + timedelta(days=61))
        self.assertEqual(far.context["form"].errors["date"], ["Requests can be made up to 60 days ahead."])
        self.assertEqual(self.request_table(today + timedelta(days=1), party="9").status_code, 200)
        self.assertFalse(Reservation.objects.exists())

    def test_same_day_requests_need_an_hour_of_notice(self):
        today = timezone.localdate()
        evening = timezone.make_aware(datetime.combine(today, time(17, 30)))
        with mock.patch("django.utils.timezone.now", return_value=evening):
            too_soon = self.request_table(today, slot="18:00")
            self.assertIn("at least 60 minutes from now", too_soon.context["form"].errors["time"][0])
            self.assertEqual(self.request_table(today, slot="19:00").status_code, 302)

    def test_a_valid_request_is_pending_until_staff_confirm_it(self):
        response = self.request_table(timezone.localdate() + timedelta(days=2), notes="Window seat if possible")
        reservation = Reservation.objects.get()
        self.assertRedirects(response, reservation.get_absolute_url())
        self.assertEqual((reservation.reference, reservation.status, reservation.party_size), ("R-00001", "pending", 3))
        self.assertContains(self.client.get(reservation.get_absolute_url()), "Pending")

    def test_guests_can_cancel_their_request_until_it_starts(self):
        self.request_table(timezone.localdate() + timedelta(days=2))
        reservation = Reservation.objects.get()
        self.client.post(reverse("lounge:reservation_cancel", args=[reservation.token]))
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "cancelled")
        past = Reservation.objects.create(name="Earlier Guest", email="guest@example.com", party_size=2,
                                          date=timezone.localdate() - timedelta(days=3), time=time(18, 0),
                                          status="confirmed")
        self.client.post(reverse("lounge:reservation_cancel", args=[past.token]))
        past.refresh_from_db()
        self.assertEqual(past.status, "confirmed")


class ContactAndNewsletterTests(TestCase):
    def send(self, message, **extra):
        return self.client.post(reverse("lounge:contact"), {
            "name": "Test Guest", "email": "guest@example.com", "topic": "general", "message": message, **extra,
        }, follow=True)

    def test_contact_messages_are_saved_once(self):
        self.assertContains(self.send("Is there a quiet corner for reading?"), "your message is saved")
        repeat = self.send("  is there a QUIET corner   for reading? ")
        self.assertContains(repeat, "already have this message")
        self.send("A different question about the menu.")
        self.assertEqual(ContactMessage.objects.count(), 2)

    def test_contact_validation_and_spam_trap(self):
        short = self.client.post(reverse("lounge:contact"), {"name": "", "email": "x", "topic": "general", "message": "Hi"})
        self.assertEqual(set(short.context["form"].errors), {"name", "email", "message"})
        self.send("Buy cheap things at my website today", website="http://spam.example")
        self.assertFalse(ContactMessage.objects.exists())

    def test_newsletter_subscribes_once_and_rejects_bad_addresses(self):
        url = reverse("lounge:newsletter")
        first = self.client.post(url, {"email": "Reader@Example.com"}, **FETCH).json()
        again = self.client.post(url, {"email": "reader@example.com "}, **FETCH).json()
        bad = self.client.post(url, {"email": "not-an-email"}, **FETCH)
        self.assertEqual((first["ok"], first["duplicate"]), (True, False))
        self.assertEqual((again["ok"], again["duplicate"]), (True, True))
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(list(NewsletterSubscriber.objects.values_list("email", flat=True)), ["reader@example.com"])
        self.client.post(url, {"email": "other@example.com", "source": '=HYPERLINK("http://x.example")'}, **FETCH)
        self.assertEqual(NewsletterSubscriber.objects.get(email="other@example.com").source, "")


class ErrorPageTests(TestCase):
    def test_friendly_error_pages(self):
        missing = self.client.get("/no-such-page/")
        self.assertContains(missing, "find that page", status_code=404)
        expired = Client(enforce_csrf_checks=True).post(reverse("lounge:contact"), {"message": "hello there"})
        self.assertContains(expired, "That form expired", status_code=403)
        crashed = server_error(RequestFactory().get("/"))
        self.assertEqual(crashed.status_code, 500)
        self.assertIn("Something went wrong on our side", crashed.content.decode())
