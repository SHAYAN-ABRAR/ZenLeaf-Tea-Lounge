# Menu photo prompts

The menu photos were generated with ChatGPT from these prompts, one image per menu item. Each prompt is
the item's description followed by the same style lines, so the photos match. `tools/prepare_photos.py`
then cropped them to 4:3 and saved them as WebP. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md#menu-photos).

To replace a photo or add one for a new picture key:

1. Generate the image with the item's description and the style lines below.
2. Run `python tools/prepare_photos.py <key>=<path to the image>` (it needs Pillow).
3. Add the photo's alt text to `PHOTOS` in `lounge/illustrations.py`. Until then the site shows the drawing.

## Style lines

Every prompt ends with:

> Photorealistic food photograph for a tea lounge menu. Set on a pale oak table in front of a plain warm cream wall that is softly out of focus. Soft natural daylight from the left, gentle shadows, calm and minimal styling, natural warm colors. Camera at a 30-degree angle. Keep the subject in the center with plenty of empty space on every side, so the picture can also be cropped to a square. Landscape format. No text, no logos, no labels, no people, no hands.

## Items

| No. | Menu item | Picture key | Description (the start of the prompt) |
| --- | --- | --- | --- |
| 01 | Sencha | `cup-green` | A cup of clear yellow-green sencha tea in a handmade matte off-white stoneware cup on a matching saucer, with a few dark green, needle-shaped tea leaves on the saucer. |
| 02 | Jasmine green | `cup-jasmine` | A cup of pale golden-green jasmine tea in a handmade matte off-white stoneware cup on a matching saucer, with two small white jasmine blossoms on the table beside it. |
| 03 | White peony | `cup-white` | A cup of very pale golden white tea in a handmade matte off-white stoneware cup on a matching saucer, with a few silvery-green tea buds and leaves on the saucer. |
| 04 | Breakfast black | `cup-dark` | A cup of strong, deep reddish-brown black tea in a handmade matte off-white stoneware cup on a matching saucer, with a small stoneware milk jug beside it. |
| 05 | Muscatel black | `cup-amber` | A cup of bright, light amber black tea in a handmade matte off-white stoneware cup on a matching saucer. The tea is clear enough to see the bottom of the cup. |
| 06 | Earl grey | `cup-bergamot` | A cup of dark amber black tea in a handmade matte off-white stoneware cup on a matching saucer, with a thin slice of lemon on the saucer. |
| 07 | Roasted oolong | `cup-roasted` | A cup of copper-brown roasted oolong tea in a handmade matte off-white stoneware cup on a matching saucer, with a few dark, tightly rolled oolong leaves on the saucer. |
| 08 | Masala chai | `mug-chai` | A handmade matte off-white stoneware mug of creamy, light-brown masala chai, with a cinnamon stick and a few green cardamom pods on the table beside it. |
| 09 | Chamomile | `cup-chamomile` | A cup of clear pale-yellow chamomile infusion in a handmade matte off-white stoneware cup on a matching saucer, with a few dried chamomile flowers beside it. |
| 10 | Peppermint | `cup-mint` | A cup of clear, light green-gold peppermint infusion in a handmade matte off-white stoneware cup on a matching saucer, with a fresh mint sprig on the saucer. |
| 11 | Rooibos vanilla | `cup-rooibos` | A cup of clear red-amber rooibos in a handmade matte off-white stoneware cup on a matching saucer, with a vanilla pod on the saucer. |
| 12 | Hibiscus & ginger | `cup-hibiscus` | A cup of deep ruby-red hibiscus infusion in a handmade matte off-white stoneware cup on a matching saucer, with a few dried hibiscus petals and two thin slices of fresh ginger beside it. |
| 13 | Matcha | `bowl-matcha` | A wide, handmade matte off-white stoneware tea bowl of bright green whisked matcha with a fine foam on top, and a bamboo whisk resting beside it. |
| 14 | Matcha latte | `mug-matcha` | A handmade matte off-white stoneware mug of pale green matcha latte, with a leaf pattern drawn in the milk foam. |
| 15 | Hojicha latte | `mug-hojicha` | A handmade matte off-white stoneware mug of light-brown hojicha latte with smooth milk foam on top. |
| 16 | Iced lemon black tea | `glass-lemon` | A tall clear glass of iced amber black tea with ice cubes and a slice of lemon, with a little condensation on the glass. |
| 17 | Cold-brew sencha | `glass-green` | A tall clear glass of pale yellow-green cold-brew sencha tea with ice cubes, with a little condensation on the glass. |
| 18 | Hibiscus cooler | `glass-hibiscus` | A tall clear glass of iced ruby-red hibiscus drink with ice cubes and a wedge of lime, with a little condensation on the glass. |
| 19 | Almond biscuits (2) | `plate-biscuits` | Two round, golden, crisp almond butter biscuits on a small handmade matte off-white stoneware plate. |
| 20 | Cardamom bun | `plate-bun` | A glazed, twisted cardamom bun with a sprinkle of sugar on a small handmade matte off-white stoneware plate. |
| 21 | Lemon loaf slice | `plate-loaf` | A slice of lemon loaf cake with a thin white sugar glaze on a small handmade matte off-white stoneware plate. |
