"""The demo menu loaded by `python manage.py seed_demo`.

Everything here is illustrative: the names describe common styles of tea rather than teas from a
named region, and the prices and availability are made up for the demo. Descriptions stick to what a
style of tea generally tastes like; they make no claims about origin, sourcing, certification or awards.
"""
from decimal import Decimal as D

CATEGORIES = [
    ("green-white", "Green & white", "Delicate teas brewed below boiling.", 1),
    ("black-oolong", "Black & oolong", "Fuller teas that suit hotter water.", 2),
    ("herbal", "Herbal", "Infusions made without the tea plant, so they're caffeine-free.", 3),
    ("matcha-lattes", "Matcha & lattes", "Whisked matcha and tea with steamed milk.", 4),
    ("iced", "Iced", "Tea served cold.", 5),
    ("bites", "Small bites", "Something to eat with your tea.", 6),
]

# slug, category, name, short description, description, price, illustration, caffeine,
# temperature (°C), steeping time, tasting notes, allergens, available, featured, sort order
PRODUCTS = [
    ("sencha", "green-white", "Sencha",
     "Steamed green tea with a fresh, grassy taste.",
     "A Japanese style of green tea. The leaves are steamed soon after picking, which keeps the color "
     "bright and the taste fresh and a little savory. It turns bitter in water that's too hot, so it's "
     "brewed well below boiling.",
     D("220"), "cup-green", "medium", 75, "1–2 min", "grassy, bright, savory", "", True, True, 1),
    ("jasmine-green", "green-white", "Jasmine green",
     "Green tea scented with jasmine blossoms.",
     "Green tea is left to rest with fresh jasmine flowers until it takes on their scent. The cup is "
     "light and floral, with a clean finish.",
     D("240"), "cup-jasmine", "medium", 80, "2–3 min", "floral, sweet, clean", "", True, False, 2),
    ("white-peony", "green-white", "White peony",
     "A soft white tea with gentle, honeyed notes.",
     "White teas are simply withered and dried. This style uses buds and young leaves together, so the "
     "cup is soft and mellow with a hint of honey.",
     D("280"), "cup-white", "low", 80, "3–4 min", "honey, hay, melon", "", True, False, 3),
    ("breakfast-black", "black-oolong", "Breakfast black",
     "Malty black tea that takes milk well.",
     "A strong, malty black tea that works plain or with a splash of milk.",
     D("200"), "cup-dark", "high", 95, "3–4 min", "malty, bold", "", True, False, 1),
    ("muscatel-black", "black-oolong", "Muscatel black",
     "Light-bodied black tea with a muscatel character.",
     "A black tea that is lighter than most, with a fruity, grape-like note often described as "
     "muscatel. Best without milk.",
     D("260"), "cup-amber", "medium", 90, "3 min", "muscatel, floral, brisk", "", True, False, 2),
    ("earl-grey", "black-oolong", "Earl grey",
     "Black tea flavored with bergamot.",
     "Black tea flavored with oil of bergamot, a fragrant citrus. Good plain or with a slice of lemon.",
     D("220"), "cup-bergamot", "high", 95, "3–4 min", "citrus, floral", "", True, False, 3),
    ("roasted-oolong", "black-oolong", "Roasted oolong",
     "Toasty, rounded oolong with a stone-fruit sweetness.",
     "Oolong sits between green and black tea. A slow roast gives this style toasty, nutty notes. "
     "The leaves can be steeped several times.",
     D("300"), "cup-roasted", "medium", 95, "2–3 min", "toasty, nutty, stone fruit", "", True, False, 4),
    ("masala-chai", "black-oolong", "Masala chai",
     "Black tea simmered with milk, ginger and warm spices.",
     "Black tea simmered with milk, ginger, cardamom and cinnamon, then lightly sweetened.",
     D("180"), "mug-chai", "high", None, "", "spiced, creamy, warming", "Contains milk", True, True, 5),
    ("chamomile", "herbal", "Chamomile",
     "Whole chamomile flowers; soft and apple-like.",
     "Dried chamomile flowers make a gentle, slightly sweet infusion with an apple-like aroma.",
     D("180"), "cup-chamomile", "none", 100, "5 min", "apple, honey, soft", "", True, False, 1),
    ("peppermint", "herbal", "Peppermint",
     "Peppermint leaves; cool and clean.",
     "A simple infusion of dried peppermint leaves. Cooling and bright.",
     D("160"), "cup-mint", "none", 100, "5 min", "cool, clean, sweet", "", True, False, 2),
    ("rooibos-vanilla", "herbal", "Rooibos vanilla",
     "Red bush infusion with vanilla; smooth and naturally caffeine-free.",
     "Rooibos comes from a South African shrub rather than the tea plant. It brews red, smooth and "
     "slightly sweet; the vanilla rounds it out.",
     D("220"), "cup-rooibos", "none", 100, "5–6 min", "vanilla, smooth, sweet", "", True, False, 3),
    ("hibiscus-ginger", "herbal", "Hibiscus & ginger",
     "Tart hibiscus with a little ginger warmth.",
     "Dried hibiscus gives a deep red, tart infusion. A little ginger adds warmth.",
     D("200"), "cup-hibiscus", "none", 100, "5–7 min", "tart, berry, ginger", "", True, False, 4),
    ("matcha", "matcha-lattes", "Matcha",
     "Whisked matcha, bright and vegetal.",
     "Matcha is green tea ground to a fine powder and whisked with hot water, so you drink the whole "
     "leaf. It's served thin, in the style called usucha.",
     D("320"), "bowl-matcha", "high", 80, "whisk 20 s", "vegetal, creamy, umami", "", True, False, 1),
    ("matcha-latte", "matcha-lattes", "Matcha latte",
     "Matcha whisked into steamed milk.",
     "Matcha whisked with a little water, then topped with steamed milk.",
     D("350"), "mug-matcha", "medium", None, "", "creamy, vegetal", "Contains milk", True, True, 2),
    ("hojicha-latte", "matcha-lattes", "Hojicha latte",
     "Roasted green tea with steamed milk; nutty and low in caffeine.",
     "Hojicha is green tea roasted until brown, which softens it and lowers the caffeine. With steamed "
     "milk it tastes nutty and gently sweet.",
     D("330"), "mug-hojicha", "low", None, "", "roasted, nutty, caramel", "Contains milk", True, False, 3),
    ("iced-lemon-black", "iced", "Iced lemon black tea",
     "Chilled black tea with lemon.",
     "Black tea brewed strong, chilled over ice and finished with lemon.",
     D("190"), "glass-lemon", "high", None, "", "citrus, brisk", "", True, False, 1),
    ("cold-brew-sencha", "iced", "Cold-brew sencha",
     "Sencha steeped cold for a sweeter, gentler cup.",
     "Steeping sencha in cold water for several hours draws out less bitterness, so the tea tastes "
     "sweeter and softer.",
     D("240"), "glass-green", "medium", None, "", "sweet, grassy, smooth", "", True, True, 2),
    ("hibiscus-cooler", "iced", "Hibiscus cooler",
     "Iced hibiscus with lime.",
     "Hibiscus infusion served over ice with a squeeze of lime.",
     D("210"), "glass-hibiscus", "none", None, "", "tart, bright", "", False, False, 3),
    ("almond-biscuits", "bites", "Almond biscuits (2)",
     "Two crisp, buttery biscuits.",
     "Two crisp butter biscuits with ground almonds.",
     D("150"), "plate-biscuits", "", None, "", "", "Contains wheat, milk, almonds", True, False, 1),
    ("cardamom-bun", "bites", "Cardamom bun",
     "A soft sweet bun with cardamom sugar.",
     "An enriched sweet bun rolled with cardamom sugar and glazed.",
     D("180"), "plate-bun", "", None, "", "", "Contains wheat, milk, egg", True, False, 2),
    ("lemon-loaf", "bites", "Lemon loaf slice",
     "A slice of lemon loaf cake.",
     "A slice of lemon loaf cake with a thin sugar glaze.",
     D("170"), "plate-loaf", "", None, "", "", "Contains wheat, milk, egg", False, False, 3),
]
