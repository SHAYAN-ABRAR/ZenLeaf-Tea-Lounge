# Third-party notices

## Included in this repository

| Files | Work | Copyright | License |
| --- | --- | --- | --- |
| `lounge/static/lounge/fonts/fraunces-latin-opsz-normal.woff2` | Fraunces (variable, Latin subset) | Copyright 2020 The Fraunces Project Authors | SIL Open Font License 1.1, full text in `lounge/static/lounge/fonts/OFL-Fraunces.txt` |
| `lounge/static/lounge/fonts/manrope-latin-wght-normal.woff2` | Manrope (variable, Latin subset) | Copyright 2019 The Manrope Project Authors | SIL Open Font License 1.1, full text in `lounge/static/lounge/fonts/OFL-Manrope.txt` |

Both font files are unmodified copies of the files published in the npm packages
`@fontsource-variable/fraunces` 5.3.0 and `@fontsource-variable/manrope` 5.3.0 (their SHA-256 hashes
match). The license texts are copied unchanged from those packages.

## Installed at setup time, not included

These are downloaded from PyPI by `python bootstrap.py` (see `requirements.txt`). Their licenses
travel with the installed packages.

| Package | License |
| --- | --- |
| Django 5.2 | BSD 3-Clause |
| WhiteNoise 6.12 | MIT |

## Made for this project

The product illustrations, hero picture, logo, favicon and icons are SVG files drawn for this
project; `tools/make_illustrations.py` regenerates the illustrations. The site copy and the demo menu
were also written for this project. The menu shows an item's illustration when it has no photo.

## Menu photos

The photos in `lounge/static/lounge/img/menu/photos/` are AI-generated. They were made in September
2026 with ChatGPT's image generation (OpenAI), from prompts written for this project and listed in
`docs/photo-prompts.md`. The original files carried Content Credentials (C2PA) naming ChatGPT as their
source. `tools/prepare_photos.py` cropped them to 4:3 and saved them as WebP, which leaves that
metadata out. The photos don't show real products, people or places. Their use is subject to
OpenAI's terms of use.

## Earlier version

The earlier static landing page, which is still in the repository's history (up to commit `be75543`),
used a third-party template. Its footer carried the line "© 2027 UIDesign.to - All rights reserved."
No markup, styles, images or text from that page are used in the current site. See `docs/asset-audit.md`.
