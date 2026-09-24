"""The product illustrations that ship with the project (static/lounge/img/menu/<key>.svg).

They were drawn for this project by tools/make_illustrations.py. Each entry has a short label for
the staff product form and a description used as alt text on product pages.
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


def illustration_alt(key):
    return ILLUSTRATIONS.get(key, ("", "Illustration of a drink"))[1]
