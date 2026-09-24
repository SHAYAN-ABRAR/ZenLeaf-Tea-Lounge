"""The database layer: migrations, the demo seed, order placement, and backup/restore."""
import sqlite3
import tempfile
from contextlib import closing
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase, override_settings

from lounge.models import Category, Order, Product

from .utils import product, seed


class MigrationTests(TestCase):
    def test_models_and_migrations_agree(self):
        # Exits with an error if a model change is missing its migration.
        call_command("makemigrations", "--check", "--dry-run", stdout=StringIO())


class SeedTests(TestCase):
    def test_seed_loads_the_demo_menu(self):
        seed()
        self.assertEqual(Category.objects.count(), 6)
        self.assertEqual(Product.objects.count(), 21)
        self.assertEqual(
            set(Product.objects.filter(is_available=False).values_list("slug", flat=True)),
            {"hibiscus-cooler", "lemon-loaf"},
        )
        self.assertEqual(Product.objects.filter(is_featured=True).count(), 4)

    def test_running_the_seed_again_keeps_staff_changes_unless_reset(self):
        seed()
        Product.objects.filter(slug="sencha").update(price=Decimal("999"), is_available=False)
        seed()
        self.assertEqual(Product.objects.count(), 21)
        self.assertEqual(product("sencha").price, Decimal("999"))
        call_command("seed_demo", "--reset", stdout=StringIO())
        sencha = product("sencha")
        self.assertEqual((sencha.price, sencha.is_available), (Decimal("220"), True))

    def test_bootstrap_seed_leaves_an_existing_menu_alone(self):
        seed()
        product("matcha").delete()
        call_command("seed_demo", "--if-empty", stdout=StringIO())     # what bootstrap.py runs
        self.assertFalse(Product.objects.filter(slug="matcha").exists())
        seed()                                                          # an explicit seed_demo adds it back
        self.assertTrue(Product.objects.filter(slug="matcha").exists())


class OrderModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def place(self, lines, key=None):
        return Order.place(customer_name="Test Guest", email="guest@example.com", phone="", notes="",
                           lines=lines, checkout_key=key)

    def test_place_prices_items_from_the_database_and_numbers_orders(self):
        order = self.place([(product("sencha"), 2), (product("masala-chai"), 1)])
        self.assertEqual(order.number, "ZL-00001")
        self.assertEqual(order.subtotal, Decimal("620"))          # 2 × 220 + 180
        self.assertEqual(order.item_count, 3)
        self.assertEqual([(i.product_name, i.unit_price, i.quantity) for i in order.items.all()],
                         [("Sencha", Decimal("220"), 2), ("Masala chai", Decimal("180"), 1)])
        self.assertEqual(order.status, Order.Status.RECEIVED)
        self.assertEqual(self.place([(product("matcha"), 1)]).number, "ZL-00002")

    def test_order_history_survives_product_changes_and_deletion(self):
        order = self.place([(product("peppermint"), 1)])
        Product.objects.filter(slug="peppermint").update(price=Decimal("500"))
        product("peppermint").delete()
        item = order.items.get()
        self.assertIsNone(item.product)
        self.assertEqual((item.product_name, item.line_total), ("Peppermint", Decimal("160")))

    def test_a_checkout_key_can_only_create_one_order(self):
        self.place([(product("sencha"), 1)], key="same-form")
        with self.assertRaises(IntegrityError):
            self.place([(product("sencha"), 1)], key="same-form")


class BackupRestoreTests(TransactionTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        override = override_settings(ZENLEAF={**settings.ZENLEAF, "BACKUP_DIR": str(self.folder)})
        override.enable()
        self.addCleanup(override.disable)
        seed()

    def test_backup_then_restore_brings_the_data_back(self):
        Order.place(customer_name="Test Guest", email="guest@example.com", phone="", notes="",
                    lines=[(product("sencha"), 1)])
        backup = self.folder / "backup.sqlite3"
        call_command("backup_db", "--output", str(backup), stdout=StringIO())

        with closing(sqlite3.connect(backup)) as copy:   # a complete, self-contained SQLite file
            self.assertEqual(copy.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(copy.execute("PRAGMA journal_mode").fetchone()[0], "delete")
            self.assertEqual(copy.execute("SELECT number FROM lounge_order").fetchall(), [("ZL-00001",)])

        Order.objects.all().delete()
        call_command("restore_db", str(backup), "--yes", stdout=StringIO())
        self.assertEqual(list(Order.objects.values_list("number", flat=True)), ["ZL-00001"])
        self.assertEqual(len(list(self.folder.glob("before-restore-*.sqlite3"))), 1)

    def test_restore_refuses_files_that_are_not_zenleaf_backups(self):
        other = self.folder / "other.sqlite3"
        with closing(sqlite3.connect(other)) as db:
            db.execute("CREATE TABLE notes (body TEXT)")
        with self.assertRaisesMessage(CommandError, "doesn't look like a ZenLeaf database"):
            call_command("restore_db", str(other), "--yes", stdout=StringIO())
        not_sqlite = self.folder / "notes.txt"
        not_sqlite.write_text("hello")
        with self.assertRaisesMessage(CommandError, "isn't a readable SQLite database"):
            call_command("restore_db", str(not_sqlite), "--yes", stdout=StringIO())
        self.assertEqual(Product.objects.count(), 21)       # nothing was replaced
