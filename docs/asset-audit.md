# Asset and copy audit

This records what the earlier static page (`index.html`, last present in commit `be75543`) contained,
and what happened to each part in the full-stack rebuild.

## Findings in the earlier page

| Item | What was there | Problem |
| --- | --- | --- |
| Brand and copy | Hero headline "It's good tea time at The Tea House"; intro paragraphs in Lorem Ipsum | Another business name, and placeholder text |
| Products | Four cards, all titled "Milk Tea" with the same description | Repeated placeholder content |
| Reviews | Three identical quotes, each signed "Mr. ABC" | Invented testimonials |
| Rating badge | "5.00" with "Trust Pilot Rating" | A rating with no source, naming a real review service |
| Image alt text | "Shoes" on every product image | Left over from a DaisyUI example |
| Controls | Explore More button, footer links, newsletter field | Not connected to anything |
| Layout | Hero wider than the screen below about 416px | Sideways scrolling on phones |
| Footer notice | "© 2027 UIDesign.to - All rights reserved." | Suggests the design came from a UIDesign.to template |
| Images | 15 PNG files in `images/` | No source or license information anywhere in the repository |
| `tailwind.config.js` | Tailwind config | Not used by the page (it loaded the Play CDN) |

## Decisions

- **Images:** none of the 15 images had clear usage rights, so none were kept. The new site uses SVG
  illustrations drawn for the project (`tools/make_illustrations.py`).
- **Template, markup and copy:** replaced completely. Nothing from the earlier page is reused, so its
  "UIDesign.to" notice does not apply to the new files. The earlier page and its notice remain in the
  repository's history.
- **Screenshots and GIF of the earlier page** (`screenshots/`): removed because they show a page the
  site no longer contains. They remain in the repository's history.
- **Reviews and ratings:** removed with no replacement. The site has no real customers, so it shows no
  reviews, ratings or testimonials.
- **Business details:** the site states that the lounge is imaginary. It has no street address, phone
  number, opening-hours promise or delivery promise. The reservation hours are demo settings in
  `.env`, labelled as such.
- **Menu:** the seed menu names common styles of tea and describes how they generally taste. It avoids
  region names, origin claims, certifications and awards. The menu page and the demo notice at the top
  of every page say that prices and availability are examples.
- **Fonts:** Fraunces and Manrope under the SIL Open Font License 1.1, with the license texts next to
  the font files. See `THIRD_PARTY_NOTICES.md`.
