#!/usr/bin/env python3
"""Draw the product illustrations, the home-page illustration and the logo as SVG files.

Everything is built from simple shapes in one consistent style (ink outlines, flat fills and a
"tea ring" behind each drink), so the artwork belongs to this project. Run it again after changing
a color or adding a product style:

    python tools/make_illustrations.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "lounge" / "static" / "lounge" / "img"

INK = "#22352b"
CERAMIC = "#fffdf7"
SHADE = "#efe6d4"
SAUCER = "#f3ecdf"
LEAF = "#5f8c62"
LEAF_DARK = "#2e5a43"
def stroke(width=4):
    return f'stroke="{INK}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"'


def mix(hex_a, hex_b, t):
    """Blend two #rrggbb colors; t=0 gives a, t=1 gives b."""
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def svg(body, title, w=480, h=360):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img">'
            f"<title>{title}</title>{body}</svg>\n")


def backdrop(color, cx=240, cy=196, r=148):
    tint = mix(color, "#f6f1e7", 0.8)
    ring = mix(color, "#f6f1e7", 0.45)
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{tint}"/>'
            f'<circle cx="{cx + 6}" cy="{cy - 4}" r="{r + 10}" fill="none" stroke="{ring}" stroke-width="3" '
            f'stroke-dasharray="520 60 140 40" stroke-linecap="round"/>')


def steam(x=240, top=70, spread=34):
    paths = []
    for i, dx in enumerate((-spread, 0, spread)):
        sx = x + dx
        paths.append(
            f'<path d="M{sx} {top + 52 + (i % 2) * 6} c-12 -12 12 -20 0 -32 c-10 -10 8 -16 2 -26" fill="none" '
            f'stroke="{INK}" stroke-opacity=".32" stroke-width="4" stroke-linecap="round"/>'
        )
    return "".join(paths)


def leaf(x, y, angle=0, scale=1.0, fill=LEAF):
    return (f'<g transform="translate({x} {y}) rotate({angle}) scale({scale})">'
            f'<path d="M0 0 C 14 -22, 46 -26, 62 -8 C 46 12, 16 14, 0 0 Z" fill="{fill}" {stroke(3)}/>'
            f'<path d="M4 -1 C 22 -8, 40 -10, 56 -8" fill="none" stroke="{LEAF_DARK}" stroke-width="2.5" stroke-linecap="round"/>'
            f"</g>")


def citrus(x, y, r=22, color="#f1c84b", rind="#d99a1f"):
    segs = "".join(
        f'<path d="M{x} {y} L{x + (r - 5) * c:.1f} {y + (r - 5) * s:.1f}" stroke="{rind}" stroke-width="2" stroke-linecap="round"/>'
        for c, s in ((1, 0), (0.5, 0.866), (-0.5, 0.866), (-1, 0), (-0.5, -0.866), (0.5, -0.866))
    )
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" {stroke(3)}/>'
            f'<circle cx="{x}" cy="{y}" r="{r - 5}" fill="none" stroke="#fff6d8" stroke-width="2"/>' + segs)


def blossom(x, y, petal="#ffffff", centre="#f2c94c", r=9):
    petals = "".join(
        f'<ellipse cx="{x}" cy="{y - r}" rx="{r * 0.62:.1f}" ry="{r:.1f}" fill="{petal}" {stroke(2.5)} '
        f'transform="rotate({a} {x} {y})"/>'
        for a in range(0, 360, 72)
    )
    return petals + f'<circle cx="{x}" cy="{y}" r="{r * 0.55:.1f}" fill="{centre}" {stroke(2.5)}/>'


def daisy(x, y):
    petals = "".join(
        f'<ellipse cx="{x}" cy="{y - 13}" rx="4.5" ry="10" fill="#ffffff" stroke="{INK}" stroke-width="2" '
        f'transform="rotate({a} {x} {y})"/>' for a in range(0, 360, 30)
    )
    return petals + f'<circle cx="{x}" cy="{y}" r="8" fill="#f2c14b" stroke="{INK}" stroke-width="2.5"/>'


def mint_sprig(x, y, angle=-20):
    return (f'<g transform="translate({x} {y}) rotate({angle})">'
            f'<path d="M0 0 L0 -30" stroke="{LEAF_DARK}" stroke-width="3" stroke-linecap="round"/>'
            + leaf(0, -12, -140, 0.45, "#6fa06a") + leaf(0, -22, -40, 0.45, "#6fa06a")
            + leaf(0, -30, -95, 0.4, "#7caf73") + "</g>")


# --- vessels ----------------------------------------------------------------------------------------

def cup_body(liquor):
    """Saucer, handle, cup and tea, drawn on the 480 × 360 product canvas."""
    return (f'<ellipse cx="240" cy="272" rx="152" ry="27" fill="{SAUCER}" {stroke()}/>'
            f'<ellipse cx="240" cy="268" rx="92" ry="14" fill="none" stroke="{INK}" stroke-opacity=".35" stroke-width="3"/>'
            # handle: dark outline with a ceramic core
            f'<path d="M322 176 C 372 170, 372 236, 312 236" fill="none" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>'
            f'<path d="M322 176 C 372 170, 372 236, 312 236" fill="none" stroke="{CERAMIC}" stroke-width="8" stroke-linecap="round"/>'
            f'<path d="M148 156 C 150 222, 182 266, 240 266 C 298 266, 330 222, 332 156 Z" fill="{CERAMIC}" {stroke()}/>'
            f'<path d="M166 176 C 172 222, 196 248, 226 256" fill="none" stroke="{SHADE}" stroke-width="10" stroke-linecap="round"/>'
            f'<path d="M156 204 C 200 214, 280 214, 324 204" fill="none" stroke="{INK}" stroke-opacity=".22" stroke-width="3"/>'
            f'<ellipse cx="240" cy="156" rx="92" ry="19" fill="{CERAMIC}" {stroke()}/>'
            f'<ellipse cx="240" cy="158" rx="80" ry="13" fill="{liquor}"/>'
            f'<ellipse cx="214" cy="155" rx="22" ry="4" fill="#ffffff" fill-opacity=".35"/>')


def cup(liquor, garnish=""):
    return backdrop(liquor) + cup_body(liquor) + steam(240, 64) + (garnish or leaf(92, 276, -18, 0.8))


def mug(foam, body_color="#fbf6ec", art="#fffaf0", extra=""):
    out = backdrop(foam)
    out += f'<ellipse cx="240" cy="286" rx="118" ry="20" fill="{SAUCER}" {stroke()}/>'
    out += (f'<path d="M306 150 C 366 146, 368 238, 300 236" fill="none" stroke="{INK}" stroke-width="18" stroke-linecap="round"/>'
            f'<path d="M306 150 C 366 146, 368 238, 300 236" fill="none" stroke="{body_color}" stroke-width="9" stroke-linecap="round"/>')
    out += (f'<path d="M162 118 L 172 268 Q 174 282 190 282 L 290 282 Q 306 282 308 268 L 318 118 Z" fill="{body_color}" {stroke()}/>'
            f'<path d="M182 140 L 190 262" stroke="{SHADE}" stroke-width="10" stroke-linecap="round"/>')
    out += (f'<ellipse cx="240" cy="118" rx="78" ry="16" fill="{body_color}" {stroke()}/>'
            f'<ellipse cx="240" cy="120" rx="68" ry="11" fill="{foam}"/>'
            f'<path d="M216 120 C 226 110, 252 110, 262 120 C 252 128, 226 128, 216 120 Z" fill="{art}"/>'
            f'<path d="M222 120 L 258 120" stroke="{foam}" stroke-width="2"/>')
    out += steam(240, 30, 28)
    out += extra
    return out


def bowl(color):
    out = backdrop(color, cy=200)
    out += f'<ellipse cx="240" cy="284" rx="126" ry="20" fill="{SAUCER}" {stroke()}/>'
    out += (f'<path d="M126 176 C 132 250, 186 280, 240 280 C 294 280, 348 250, 354 176 Z" fill="#e9dcc3" {stroke()}/>'
            f'<path d="M148 200 C 170 250, 206 266, 240 268" fill="none" stroke="#d8c7a6" stroke-width="10" stroke-linecap="round"/>'
            f'<path d="M140 236 C 200 246, 280 246, 340 236" fill="none" stroke="{INK}" stroke-opacity=".2" stroke-width="3"/>')
    out += (f'<ellipse cx="240" cy="176" rx="114" ry="24" fill="#e9dcc3" {stroke()}/>'
            f'<ellipse cx="240" cy="178" rx="102" ry="18" fill="{color}"/>')
    foam = mix(color, "#ffffff", 0.45)
    out += "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{foam}"/>' for x, y, r in (
        (206, 176, 5), (222, 182, 4), (240, 174, 6), (258, 181, 4), (274, 175, 5), (230, 170, 3), (252, 170, 3),
        (286, 181, 3), (196, 183, 3)))
    # bamboo whisk
    out += (f'<g transform="translate(384 206) rotate(18)">'
            f'<rect x="-9" y="0" width="18" height="70" rx="6" fill="#d8b77a" {stroke(3)}/>'
            f'<path d="M-18 0 C -20 -38, 20 -38, 18 0 Z" fill="#f0dfb6" {stroke(3)}/>'
            f'<path d="M-9 -4 C -8 -24, 8 -24, 9 -4 M0 -2 L0 -28" fill="none" stroke="{INK}" stroke-opacity=".45" stroke-width="2"/></g>')
    return out


def glass(liquor, garnish):
    out = backdrop(liquor, cy=196)
    out += f'<ellipse cx="240" cy="300" rx="92" ry="14" fill="{SAUCER}" {stroke()}/>'
    out += (f'<path d="M188 128 L 200 290 Q 202 298 212 298 L 268 298 Q 278 298 280 290 L 292 128 Z" fill="{liquor}"/>'
            f'<path d="M186 98 L 200 290 Q 202 298 212 298 L 268 298 Q 278 298 280 290 L 294 98" fill="#ffffff" '
            f'fill-opacity=".25" {stroke()}/>'
            f'<ellipse cx="240" cy="98" rx="54" ry="9" fill="#ffffff" fill-opacity=".5" {stroke()}/>'
            f'<ellipse cx="240" cy="128" rx="51" ry="7" fill="{mix(liquor, "#ffffff", 0.3)}"/>')
    cubes = ((214, 150, -8), (250, 168, 10), (226, 196, 4))
    out += "".join(
        f'<rect x="{x}" y="{y}" width="30" height="28" rx="6" fill="#ffffff" fill-opacity=".55" stroke="{INK}" '
        f'stroke-opacity=".45" stroke-width="2.5" transform="rotate({a} {x + 15} {y + 14})"/>' for x, y, a in cubes)
    out += '<path d="M204 140 L 214 280" stroke="#ffffff" stroke-opacity=".6" stroke-width="6" stroke-linecap="round"/>'
    out += f'<path d="M258 60 L 250 250" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>' \
           f'<path d="M258 60 L 250 250" stroke="#e9dfcc" stroke-width="4" stroke-linecap="round"/>'
    out += garnish
    return out


def plate(food):
    out = backdrop("#d9a55b", cy=200)
    out += (f'<ellipse cx="240" cy="262" rx="160" ry="40" fill="{CERAMIC}" {stroke()}/>'
            f'<ellipse cx="240" cy="258" rx="118" ry="26" fill="none" stroke="{INK}" stroke-opacity=".3" stroke-width="3"/>')
    return out + food


def biscuits():
    one = lambda x, y: (f'<ellipse cx="{x}" cy="{y}" rx="58" ry="20" fill="#c98f47" {stroke()}/>'
                        f'<ellipse cx="{x}" cy="{y - 7}" rx="58" ry="20" fill="#e3b46a" {stroke()}/>'
                        + "".join(f'<circle cx="{x + dx}" cy="{y - 7 + dy}" r="2.6" fill="#a8702f"/>'
                                  for dx, dy in ((-26, -4), (-8, 5), (12, -6), (28, 4), (0, -10))))
    return plate(one(200, 250) + one(282, 232) + leaf(120, 236, -30, 0.5, "#c4a26a"))


def bun():
    food = (f'<path d="M160 256 C 160 170, 320 170, 320 256 Z" fill="#c9843f" {stroke()}/>'
            f'<path d="M176 250 C 182 196, 298 196, 304 250" fill="none" stroke="#f1c98f" stroke-width="7" stroke-linecap="round" stroke-opacity=".8"/>'
            f'<path d="M198 232 C 214 206, 266 206, 282 232 M222 222 C 232 212, 250 212, 258 222" fill="none" stroke="#8a5220" stroke-width="3.5" stroke-linecap="round"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="2.8" fill="#fff4dc"/>'
                      for x, y in ((210, 214), (236, 204), (262, 212), (286, 226), (190, 234), (246, 228))))
    return plate(food)


def loaf():
    food = (f'<path d="M168 262 L 168 196 C 168 166, 312 166, 312 196 L 312 262 Z" fill="#edc873" {stroke()}/>'
            f'<path d="M168 200 C 168 170, 312 170, 312 200 L 312 206 C 296 216, 282 204, 268 214 C 252 224, 238 206, 222 216 C 206 226, 190 208, 168 216 Z" fill="#fff8e6" {stroke(3)}/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="2.6" fill="#c99a3c"/>'
                      for x, y in ((196, 236), (226, 248), (252, 232), (282, 246), (206, 254), (268, 256)))
            + citrus(348, 250, 18))
    return plate(food)


PRODUCTS = {
    "cup-green": lambda: cup("#c3cc74"),
    "cup-jasmine": lambda: cup("#d9c374", blossom(388, 262)),
    "cup-white": lambda: cup("#ead8a0"),
    "cup-amber": lambda: cup("#c7873a"),
    "cup-dark": lambda: cup("#8c4a22"),
    "cup-bergamot": lambda: cup("#96522a", citrus(392, 262)),
    "cup-roasted": lambda: cup("#a5612f"),
    "cup-chamomile": lambda: cup("#e6c56a", daisy(386, 262)),
    "cup-mint": lambda: cup("#b5c985", mint_sprig(380, 276)),
    "cup-rooibos": lambda: cup("#b0502f"),
    "cup-hibiscus": lambda: cup("#a3263e"),
    "mug-chai": lambda: mug("#c9a07a", extra=(
        f'<g transform="rotate(-24 300 110)"><rect x="236" y="100" width="110" height="12" rx="6" fill="#9a5a2c" {stroke(3)}/></g>')),
    "mug-matcha": lambda: mug("#b9cc86", art="#f5f8ea"),
    "mug-hojicha": lambda: mug("#b98a5f", art="#f3e3cf"),
    "bowl-matcha": lambda: bowl("#7da23f"),
    "glass-lemon": lambda: glass("#c9792f", citrus(300, 96, 24)),
    "glass-green": lambda: glass("#bfcb78", leaf(292, 92, -30, 0.6, "#6fa06a")),
    "glass-hibiscus": lambda: glass("#b3243f", citrus(300, 96, 24, "#a6d15a", "#6c9a2c")),
    "plate-biscuits": biscuits,
    "plate-bun": bun,
    "plate-loaf": loaf,
}


def teapot(fill="#e7efe3", shade="#cfdcc9"):
    """A round teapot centred on (0, 0), spout to the right."""
    handle = "M-86 -34 C -154 -44, -154 62, -84 52"
    spout = "M82 18 C 118 8, 130 -32, 166 -54"
    return (f'<path d="{handle}" fill="none" stroke="{INK}" stroke-width="18" stroke-linecap="round"/>'
            f'<path d="{handle}" fill="none" stroke="{fill}" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="{spout}" fill="none" stroke="{INK}" stroke-width="24" stroke-linecap="round"/>'
            f'<path d="{spout}" fill="none" stroke="{fill}" stroke-width="13" stroke-linecap="round"/>'
            f'<path d="M-92 0 C -92 -72, 92 -72, 92 0 C 92 78, 52 104, 0 104 C -52 104, -92 78, -92 0 Z" fill="{fill}" {stroke()}/>'
            f'<path d="M-74 22 C -66 62, -40 86, -8 92" fill="none" stroke="{shade}" stroke-width="12" stroke-linecap="round"/>'
            f'<path d="M-88 24 C -30 40, 30 40, 88 24" fill="none" stroke="{INK}" stroke-opacity=".22" stroke-width="3"/>'
            f'<ellipse cx="0" cy="-54" rx="62" ry="14" fill="{fill}" {stroke()}/>'
            f'<path d="M-36 -58 C -34 -86, 34 -86, 36 -58" fill="{fill}" {stroke()}/>'
            f'<circle cx="0" cy="-92" r="10" fill="{LEAF}" {stroke(3)}/>')


def hero():
    """A teapot pouring into a cup, with loose leaves: the home-page illustration."""
    tea = "#c9873c"
    body = (f'<circle cx="330" cy="270" r="220" fill="{mix("#c3cc74", "#f6f1e7", 0.78)}"/>'
            f'<circle cx="338" cy="262" r="236" fill="none" stroke="{mix("#c3cc74", "#f6f1e7", 0.4)}" stroke-width="3" '
            f'stroke-dasharray="820 70 200 50" stroke-linecap="round"/>')
    body += f'<g transform="translate(272 262) scale(0.64)">{cup_body(tea)}</g>'
    body += (f'<path d="M376 212 C 392 240, 404 300, 410 354" fill="none" stroke="{tea}" stroke-width="7" '
             f'stroke-linecap="round"/>')
    body += f'<g transform="translate(200 214) rotate(16)">{teapot()}</g>'
    body += steam(452, 286, 16)
    body += (leaf(84, 452, -10, 0.9) + leaf(512, 452, 16, 0.8, "#78a36f") + leaf(548, 420, -42, 0.6)
             + leaf(96, 118, 160, 0.55, "#78a36f"))
    body += blossom(536, 186, r=11)
    return svg(body, "A teapot pouring tea into a cup, with loose tea leaves", 640, 520)


def logo(size=64):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}">'
            f'<circle cx="32" cy="32" r="29" fill="#234b37"/>'
            f'<circle cx="33" cy="31" r="23" fill="none" stroke="#e3ebe2" stroke-opacity=".5" stroke-width="2" '
            f'stroke-dasharray="100 14 30 10" stroke-linecap="round"/>'
            f'<path d="M20 42 C 20 28, 30 20, 45 19 C 45 34, 36 43, 20 42 Z" fill="#e3ebe2"/>'
            f'<path d="M22 40 L 39 25" stroke="#234b37" stroke-width="2.6" stroke-linecap="round"/></svg>\n')


def main():
    menu_dir = OUT / "menu"
    menu_dir.mkdir(parents=True, exist_ok=True)
    for key, draw in PRODUCTS.items():
        (menu_dir / f"{key}.svg").write_text(svg(draw(), key.replace("-", " ")), encoding="utf-8")
    (OUT / "hero.svg").write_text(hero(), encoding="utf-8")
    (OUT / "logo.svg").write_text(logo(), encoding="utf-8")
    (OUT / "favicon.svg").write_text(logo(32), encoding="utf-8")
    print(f"Wrote {len(PRODUCTS)} menu illustrations, hero.svg, logo.svg and favicon.svg to {OUT}")


if __name__ == "__main__":
    main()
