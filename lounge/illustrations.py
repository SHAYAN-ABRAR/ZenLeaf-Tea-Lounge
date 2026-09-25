"""The product pictures that ship with the project.

Every key has a drawing, static/lounge/img/menu/<key>.svg, drawn for this project by
tools/make_illustrations.py. Each entry in ILLUSTRATIONS has a short label for the staff product
form and a description of the drawing, used as alt text on product pages.

Keys listed in PHOTOS also have a photo in static/lounge/img/menu/photos/ (<key>-960.webp and
<key>-480.webp, 4:3, made by tools/prepare_photos.py). The photos are AI-generated; see
THIRD_PARTY_NOTICES.md. Pages show the photo when there is one and the drawing otherwise.
"""

ILLUSTRATIONS = {
    "cup-green": ("Cup: pale green tea", "A ceramic cup of pale green tea on a saucer"),
    "cup-jasmine": ("Cup: jasmine green tea", "A cup of golden green tea with a small white blossom"),
    "cup-white": ("Cup: white tea", "A cup of very pale golden tea on a saucer"),
    "cup-amber": ("Cup: amber black tea", "A cup of amber tea on a saucer"),
    "cup-dark": ("Cup: dark black tea", "A cup of deep reddish-brown tea on a saucer"),
    "cup-bergamot": ("Cup: black tea with citrus", "A cup of dark tea with a slice of citrus on the saucer"),
    "cup-roasted": ("Cup: roasted oolong", "A cup of copper-brown tea on a saucer"),
    "cup-chamomile": ("Cup: chamomile", "A cup of pale yellow infusion with a chamomile flower"),
    "cup-mint": ("Cup: peppermint", "A cup of light green infusion with a mint sprig"),
    "cup-rooibos": ("Cup: rooibos", "A cup of red-amber infusion on a saucer"),
    "cup-hibiscus": ("Cup: hibiscus", "A cup of ruby-red infusion on a saucer"),
    "mug-chai": ("Mug: chai", "A mug of milky spiced tea with a cinnamon stick"),
    "mug-matcha": ("Mug: matcha latte", "A mug of pale green matcha latte with a leaf pattern in the foam"),
    "mug-hojicha": ("Mug: hojicha latte", "A mug of light brown roasted-tea latte"),
    "bowl-matcha": ("Bowl: matcha", "A wide bowl of bright green whisked matcha"),
    "glass-lemon": ("Glass: iced lemon tea", "A tall glass of iced amber tea with a lemon slice"),
    "glass-green": ("Glass: iced green tea", "A tall glass of iced pale green tea with a mint leaf"),
    "glass-hibiscus": ("Glass: iced hibiscus", "A tall glass of iced ruby-red infusion with a lime slice"),
    "plate-biscuits": ("Plate: biscuits", "Two round biscuits on a small plate"),
    "plate-bun": ("Plate: bun", "A glazed sweet bun on a small plate"),
    "plate-loaf": ("Plate: loaf cake", "A slice of loaf cake on a small plate"),
}

ILLUSTRATION_CHOICES = [(key, label) for key, (label, _alt) in ILLUSTRATIONS.items()]

# Alt text for the photos. A key that isn't listed here has no photo, so pages show its drawing.
PHOTOS = {
    "cup-green": "A speckled stoneware cup of clear yellow-green tea on a saucer, with a few needle-shaped tea leaves",
    "cup-bergamot": "A speckled stoneware cup of dark amber tea on a saucer, with a slice of lemon",
    "cup-roasted": "A small speckled stoneware cup of copper-brown tea on a saucer, with a few tightly rolled tea leaves",
    "cup-chamomile": "A speckled stoneware cup of pale yellow infusion on a saucer, with dried chamomile flowers beside it",
    "cup-mint": "A speckled stoneware cup of light green-gold infusion on a saucer, with a sprig of fresh mint",
    "cup-rooibos": "A speckled stoneware cup of red-amber infusion on a saucer, with a vanilla pod",
    "cup-hibiscus": "A speckled stoneware cup of ruby-red infusion on a saucer, with dried hibiscus petals and two slices of ginger beside it",
    "mug-chai": "A stoneware mug of milky spiced tea, with a cinnamon stick and green cardamom pods beside it",
    "mug-matcha": "A stoneware mug of pale green matcha latte with a leaf pattern in the milk foam",
    "mug-hojicha": "A stoneware mug of light brown latte with smooth milk foam",
    "bowl-matcha": "A stoneware bowl of bright green whisked matcha, with a bamboo whisk beside it",
    "glass-lemon": "A tall glass of iced amber tea with a slice of lemon",
    "glass-green": "A tall glass of iced pale green tea",
    "glass-hibiscus": "A tall glass of iced ruby-red drink with a wedge of lime",
    "plate-biscuits": "Two round golden almond biscuits on a small stoneware plate",
    "plate-bun": "A glazed, twisted sweet bun topped with pearl sugar on a small stoneware plate",
    "plate-loaf": "A slice of lemon loaf cake with a white glaze on a small stoneware plate",
}

# The widths each photo is saved at, in pixels (4:3, so 960 x 720 and 480 x 360).
PHOTO_WIDTHS = (960, 480)


def illustration_alt(key):
    return ILLUSTRATIONS.get(key, ("", "Illustration of a drink"))[1]


def photo_path(key, width=960):
    """The static path of the key's photo at the given width, or None when the key has no photo."""
    return f"lounge/img/menu/photos/{key}-{width}.webp" if key in PHOTOS else None


def picture_alt(key):
    """Alt text for the picture a page shows for the key: its photo if it has one, otherwise its drawing."""
    return PHOTOS.get(key) or illustration_alt(key)
