"""Menu pictures: a photo where the project has one, the drawing otherwise."""
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from lounge.illustrations import ILLUSTRATIONS, PHOTO_WIDTHS, PHOTOS, photo_path

from .utils import product, seed

STATIC = Path(settings.BASE_DIR) / "lounge" / "static"
PHOTO_DIR = STATIC / "lounge" / "img" / "menu" / "photos"


def webp_size(path):
    """Width and height of a WebP file, read from its header."""
    data = path.read_bytes()[:30]
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise AssertionError(f"{path} isn't a WebP file")
    chunk = data[12:16]
    if chunk == b"VP8 ":     # lossy
        return (int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF)
    if chunk == b"VP8L":     # lossless
        bits = int.from_bytes(data[21:25], "little")
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    if chunk == b"VP8X":     # extended
        return (int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1)
    raise AssertionError(f"{path}: unexpected WebP chunk {chunk!r}")


class PhotoFileTests(SimpleTestCase):
    def test_every_listed_photo_exists_at_both_sizes(self):
        self.assertTrue(PHOTOS)
        for key in PHOTOS:
            self.assertIn(key, ILLUSTRATIONS)
            for width in PHOTO_WIDTHS:
                path = STATIC / photo_path(key, width)
                self.assertEqual(webp_size(path), (width, width * 3 // 4), path)

    def test_the_photo_folder_holds_only_listed_photos(self):
        expected = {f"{key}-{width}.webp" for key in PHOTOS for width in PHOTO_WIDTHS}
        self.assertEqual({path.name for path in PHOTO_DIR.iterdir()}, expected)


class PicturePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def page(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_menu_cards_offer_two_photo_sizes(self):
        html = self.page(reverse("lounge:menu"))
        self.assertIn('src="/static/lounge/img/menu/photos/cup-green-480.webp"', html)
        self.assertIn("/static/lounge/img/menu/photos/cup-green-480.webp 480w, "
                      "/static/lounge/img/menu/photos/cup-green-960.webp 960w", html)
        self.assertIn('sizes="(max-width: 559px) 104px, 400px"', html)

    def test_the_product_page_describes_its_photo(self):
        html = self.page(reverse("lounge:product", args=["sencha"]))
        self.assertIn(f'alt="{PHOTOS["cup-green"]}"', html)

    def test_a_picture_without_a_photo_shows_its_drawing(self):
        with mock.patch.dict(PHOTOS, clear=True):
            html = self.page(reverse("lounge:product", args=["sencha"]))
            self.assertIsNone(product("sencha").photo_path)
        self.assertIn('src="/static/lounge/img/menu/cup-green.svg"', html)
        self.assertIn(f'alt="{ILLUSTRATIONS["cup-green"][1]}"', html)
        self.assertNotIn("img/menu/photos/", html)

    def test_the_cart_shows_small_photos(self):
        self.client.post(reverse("lounge:cart_add"), {"product_id": product("matcha-latte").pk, "quantity": "1"})
        html = self.page(reverse("lounge:cart"))
        self.assertIn('class="cart-line__art" src="/static/lounge/img/menu/photos/mug-matcha-480.webp"', html)

    def test_pages_say_the_photos_are_ai_generated(self):
        self.assertIn("Menu photos are AI-generated.", self.page(reverse("lounge:home")))
        self.assertIn("The menu photos are AI-generated", self.page(reverse("lounge:about")))

    def test_staff_picture_preview_uses_the_photo(self):
        staff = get_user_model().objects.create_user("picker", is_staff=True)   # no password: signed in directly
        self.client.force_login(staff)
        html = self.page(reverse("staff:product_edit", args=[product("sencha").pk]))
        self.assertIn('src="/static/lounge/img/menu/photos/cup-green-480.webp" alt="Preview of the selected picture"', html)
        self.assertIn('data-photo-base="/static/lounge/img/menu/photos/"', html)
        self.assertIn(f'data-photos="{" ".join(PHOTOS)}"', html)
        self.assertIn("<option value=\"\">Choose a picture</option>", html)
