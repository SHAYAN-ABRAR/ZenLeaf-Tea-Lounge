"""The online demo build (manage.py build_demo), which GitHub Pages serves."""
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from lounge.illustrations import PHOTOS

from .utils import seed


class BuildDemoTests(SimpleTestCase):
    """The build needs no database, so these tests don't use one."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "site"
        call_command("build_demo", "--output", str(cls.out), "--base-path", "/ZenLeaf-Tea-Lounge/", stdout=StringIO())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
        super().tearDownClass()

    def page(self, path):
        return (self.out / path).read_text(encoding="utf-8")

    def test_every_page_is_written_under_the_base_path(self):
        for path in ["index.html", "menu/index.html", "menu/item/index.html", "cart/index.html", "checkout/index.html",
                     "orders/index.html", "reserve/index.html", "reservations/index.html", "contact/index.html",
                     "about/index.html", "404.html", "staff/index.html", "staff/products/edit/index.html",
                     "staff/orders/view/index.html", "staff/reservations/view/index.html", "staff/subscribers/index.html"]:
            self.assertTrue((self.out / path).is_file(), path)
        home = self.page("index.html")
        self.assertIn('href="/ZenLeaf-Tea-Lounge/menu/"', home)
        self.assertIn('src="/ZenLeaf-Tea-Lounge/static/lounge/js/demo.js"', home)
        self.assertTrue((self.out / "static/lounge/css/site.css").is_file())
        self.assertTrue((self.out / "static/lounge/img/menu/cup-green.svg").is_file())

    def test_pages_are_marked_as_the_online_demo(self):
        home = self.page("index.html")
        self.assertIn("<html lang=\"en\" data-demo>", home)
        self.assertIn('data-page="home"', home)
        self.assertIn("saved only in this browser", home)
        staff = self.page("staff/index.html")
        self.assertIn("the staff area is open to everyone here", staff)
        self.assertNotIn("Sign out", staff)

    def test_no_server_only_values_end_up_in_the_files(self):
        for path in self.out.rglob("*.html"):
            html = path.read_text(encoding="utf-8")
            self.assertNotIn("csrfmiddlewaretoken", html, path)
            self.assertNotIn("/newsletter/", html, path)

    def test_demo_data_matches_the_seed_menu(self):
        text = self.page("static/lounge/js/demo-data.js")
        data = json.loads(text.split("window.ZENLEAF_DEMO = ", 1)[1].rstrip().rstrip(";"))
        self.assertEqual(data["base"], "/ZenLeaf-Tea-Lounge/")
        self.assertEqual(len(data["categories"]), 6)
        self.assertEqual(len(data["products"]), 21)
        self.assertEqual({p["slug"] for p in data["products"] if not p["is_available"]}, {"hibiscus-cooler", "lemon-loaf"})
        self.assertIn("18:00", data["settings"]["slots"])
        self.assertEqual(data["labels"]["order_status"]["preparing"], "Being prepared")
        self.assertEqual(data["photos"], PHOTOS)
        for key in PHOTOS:
            self.assertTrue((self.out / f"static/lounge/img/menu/photos/{key}-960.webp").is_file(), key)
            self.assertTrue((self.out / f"static/lounge/img/menu/photos/{key}-480.webp").is_file(), key)

    def test_it_only_replaces_its_own_output(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "notes.txt").write_text("keep me")
            with self.assertRaises(CommandError):
                call_command("build_demo", "--output", folder, stdout=StringIO())
            self.assertTrue((Path(folder) / "notes.txt").exists())
        call_command("build_demo", "--output", str(self.out), "--base-path", "/ZenLeaf-Tea-Lounge/", stdout=StringIO())
        self.assertTrue((self.out / "index.html").is_file())


class FullSiteIsUnchangedTests(TestCase):
    def test_the_django_site_does_not_load_the_demo_scripts(self):
        seed()
        html = self.client.get(reverse("lounge:home")).content.decode()
        self.assertNotIn("demo.js", html)
        self.assertNotIn("data-demo", html)
        self.assertIn("Staff sign-in", html)
