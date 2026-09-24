"""The staff area: who can get in, and that staff changes reach the database and the guest pages."""
import secrets
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from lounge.models import ContactMessage, NewsletterSubscriber, Order, Product, Reservation

from .utils import product, seed

FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}


class StaffTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()
        cls.password = secrets.token_urlsafe(16)          # throwaway, generated per test run
        User = get_user_model()
        cls.staff = User.objects.create_user("counter", password=cls.password, is_staff=True)
        cls.guest_account = User.objects.create_user("regular", password=cls.password)
        cls.order = Order.place(customer_name="Test Guest", email="guest@example.com", phone="", notes="",
                                lines=[(product("sencha"), 2)])
        cls.reservation = Reservation.objects.create(
            name="Test Guest", email="guest@example.com", date=timezone.localdate() + timedelta(days=3),
            time=time(18, 0), party_size=2)
        cls.reservation.assign_reference()
        cls.message = ContactMessage.objects.create(
            name="Test Guest", email="guest@example.com", message="Do you have oat milk?",
            fingerprint=ContactMessage.make_fingerprint("guest@example.com", "Do you have oat milk?"))
        cls.subscriber = NewsletterSubscriber.objects.create(email="reader@example.com", source="footer")

    def setUp(self):
        cache.clear()                                      # login lockout counters live in the cache

    def staff_urls(self):
        p = product("sencha").pk
        return [reverse("staff:dashboard"), reverse("staff:products"), reverse("staff:product_new"),
                reverse("staff:product_edit", args=[p]), reverse("staff:product_delete", args=[p]),
                reverse("staff:orders"), reverse("staff:order_detail", args=[self.order.pk]),
                reverse("staff:reservations"), reverse("staff:reservation_detail", args=[self.reservation.pk]),
                reverse("staff:messages"), reverse("staff:message_detail", args=[self.message.pk]),
                reverse("staff:subscribers"), reverse("staff:subscriber_export")]


class AccessTests(StaffTestCase):
    def test_signed_out_visitors_are_sent_to_sign_in(self):
        for url in self.staff_urls():
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('staff:login')}?next={url}", fetch_redirect_response=False)

    def test_accounts_without_staff_access_are_refused(self):
        self.client.force_login(self.guest_account)
        self.assertEqual(self.client.get(reverse("staff:dashboard")).status_code, 403)
        self.client.logout()
        response = self.client.post(reverse("staff:login"), {"username": "regular", "password": self.password})
        self.assertContains(response, "have access to the staff area")

    def test_staff_can_open_every_page(self):
        self.client.force_login(self.staff)
        for url in self.staff_urls():
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_sign_in_locks_after_repeated_failures(self):
        url = reverse("staff:login")
        for _ in range(5):
            self.assertContains(self.client.post(url, {"username": "counter", "password": "wrong"}), "match a staff account")
        locked = self.client.post(url, {"username": "counter", "password": self.password})
        self.assertContains(locked, "Too many failed attempts")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_correct_password_signs_in_and_sign_out_needs_post(self):
        response = self.client.post(reverse("staff:login"), {"username": "counter", "password": self.password})
        self.assertRedirects(response, reverse("staff:dashboard"))
        self.assertEqual(self.client.get(reverse("staff:logout")).status_code, 405)
        self.client.post(reverse("staff:logout"))
        self.assertEqual(self.client.get(reverse("staff:dashboard")).status_code, 302)

    def test_changes_require_a_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        url = reverse("staff:product_toggle", args=[product("sencha").pk, "is_available"])
        self.assertEqual(client.post(url, **FETCH).status_code, 403)
        self.assertTrue(product("sencha").is_available)


class StaffUpdateTests(StaffTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_marking_a_product_sold_out_updates_the_menu(self):
        url = reverse("staff:product_toggle", args=[product("sencha").pk, "is_available"])
        self.assertEqual(self.client.post(url, **FETCH).json()["value"], False)
        self.assertContains(self.client.get(reverse("lounge:product", args=["sencha"])), "sold out right now")
        bad = self.client.post(reverse("staff:product_toggle", args=[product("sencha").pk, "price"]), **FETCH)
        self.assertEqual(bad.status_code, 400)

    def test_adding_and_editing_a_product(self):
        data = {"name": "Genmaicha", "slug": "", "category": product("sencha").category_id, "price": "230",
                "short_description": "Green tea with toasted rice.", "description": "", "illustration": "cup-green",
                "caffeine": "low", "brew_temperature_c": "85", "brew_time": "2 min", "tasting_notes": "toasty",
                "allergens": "", "is_listed": "on", "is_available": "on", "sort_order": "9"}
        self.assertRedirects(self.client.post(reverse("staff:product_new"), data), reverse("staff:products"))
        created = product("genmaicha")
        self.assertContains(self.client.get(created.get_absolute_url()), "Genmaicha")
        self.client.post(reverse("staff:product_edit", args=[created.pk]), {**data, "slug": "genmaicha", "price": "240"})
        self.assertEqual(str(product("genmaicha").price), "240.00")
        missing = self.client.post(reverse("staff:product_new"), {**data, "name": "", "price": "0"})
        self.assertEqual(set(missing.context["form"].errors), {"name", "price", "slug"})

    def test_deleting_a_product_keeps_past_orders(self):
        sencha = product("sencha")
        self.client.post(reverse("staff:product_delete", args=[sencha.pk]))
        self.assertFalse(Product.objects.filter(pk=sencha.pk).exists())
        self.assertEqual(self.order.items.get().product_name, "Sencha")

    def test_order_status_update_is_shown_to_the_guest(self):
        url = reverse("staff:order_detail", args=[self.order.pk])
        self.client.post(url, {"status": "ready", "staff_note": "On the shelf by the door."})
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.staff_note), ("ready", "On the shelf by the door."))
        guest_page = Client().get(self.order.get_absolute_url())
        self.assertContains(guest_page, "Ready for pickup")
        self.assertNotContains(guest_page, "On the shelf")         # the internal note stays internal

    def test_confirming_a_table_request_with_a_note(self):
        url = reverse("staff:reservation_detail", args=[self.reservation.pk])
        self.client.post(url, {"status": "confirmed", "guest_message": "The window table is yours."})
        guest_page = Client().get(self.reservation.get_absolute_url())
        self.assertContains(guest_page, "Confirmed")
        self.assertContains(guest_page, "The window table is yours.")

    def test_reading_and_handling_messages(self):
        self.client.get(reverse("staff:message_detail", args=[self.message.pk]))
        self.client.post(reverse("staff:message_toggle", args=[self.message.pk]))
        self.message.refresh_from_db()
        self.assertIsNotNone(self.message.read_at)
        self.assertTrue(self.message.is_handled)

    def test_subscriber_export_and_removal(self):
        export = self.client.get(reverse("staff:subscriber_export"))
        self.assertEqual(export["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("reader@example.com,footer", export.content.decode())
        self.client.post(reverse("staff:subscriber_delete", args=[self.subscriber.pk]))
        self.assertFalse(NewsletterSubscriber.objects.exists())
