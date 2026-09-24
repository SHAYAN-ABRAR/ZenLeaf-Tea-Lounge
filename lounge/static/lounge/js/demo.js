/* ZenLeaf Tea Lounge: the online demo, a browser-only edition of the site for GitHub Pages.

   The full site keeps its data in a SQLite database on a Django server. GitHub Pages can only serve
   files, so this edition keeps the same kinds of data in the visitor's browser (localStorage)
   instead. Each visitor has their own copy, and the staff area is open to everyone.

   The pages themselves are built from the site's Django templates by `manage.py build_demo`; this
   script fills in everything that depends on data. The rules and messages mirror lounge/forms.py
   and lounge/views/, so both editions behave the same way. */
(function () {
  "use strict";

  const DATA = window.ZENLEAF_DEMO;
  if (!DATA || !document.documentElement.hasAttribute("data-demo")) return;

  const UI = window.ZenLeafUI || { showToast() {}, updateCartCount() {} };
  const CONF = DATA.settings;
  const LABELS = DATA.labels;
  const PAGE = document.body.getAttribute("data-page") || "";
  const params = new URLSearchParams(window.location.search);

  /* Helpers ------------------------------------------------------------------------------------ */

  const $ = (selector, root) => (root || document).querySelector(selector);
  const $all = (selector, root) => Array.from((root || document).querySelectorAll(selector));
  const url = (path) => DATA.base + (path || "");
  const go = (path) => window.location.assign(url(path));
  const reload = () => window.location.reload();
  const param = (name) => (params.get(name) || "").trim();

  const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ESCAPES[c]);
  }

  function icon(name, extraClass) {
    const body = DATA.icons[name];
    if (!body) return "";
    const cls = extraClass ? "icon " + extraClass : "icon";
    return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${body}</svg>`;
  }

  const plural = (n, one, many) => (n === 1 ? one : many || one + "s");

  function money(value) {
    const amount = Math.round(Number(value) * 100) / 100;
    const whole = Math.abs(amount - Math.round(amount)) < 1e-9;
    const digits = whole ? 0 : 2;
    return CONF.currency_symbol + " " + amount.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  /* Dates and times, formatted like the Django templates ("24 September 2026", "6:30 pm"). */
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const pad = (n) => (n < 10 ? "0" : "") + n;
  const isoDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const startOfToday = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
  const addDays = (d, days) => { const copy = new Date(d); copy.setDate(copy.getDate() + days); return copy; };

  function parseDate(value) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
    if (!m) return null;
    const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    return d.getMonth() === Number(m[2]) - 1 && d.getDate() === Number(m[3]) ? d : null;
  }

  function formatDate(d, style) {
    const day = DAYS[d.getDay()], month = MONTHS[d.getMonth()], j = d.getDate(), y = d.getFullYear();
    switch (style) {
      case "long": return `${day}, ${j} ${month} ${y}`;              // l, j F Y
      case "full": return `${day} ${j} ${month} ${y}`;               // l j F Y
      case "short": return `${j} ${month.slice(0, 3)}`;              // j M
      case "short-year": return `${j} ${month.slice(0, 3)} ${y}`;    // j M Y
      case "weekday": return `${day.slice(0, 3)} ${j} ${month.slice(0, 3)} ${y}`;  // D j M Y
      case "weekday-short": return `${day.slice(0, 3)} ${j} ${month.slice(0, 3)}`; // D j M
      default: return `${j} ${month} ${y}`;                          // j F Y
    }
  }

  const clock = (hours, minutes) => `${hours % 12 || 12}:${pad(minutes)} ${hours < 12 ? "am" : "pm"}`;
  const clockOf = (d) => clock(d.getHours(), d.getMinutes());
  const slotClock = (slot) => { const [h, m] = slot.split(":").map(Number); return clock(h, m); };
  const slotDate = (date, slot) => { const d = parseDate(date); const [h, m] = slot.split(":").map(Number); d.setHours(h, m, 0, 0); return d; };

  function localIso(d) {   // 2026-09-25T02:16+06:00, like the Django CSV export
    const offset = -d.getTimezoneOffset();
    const sign = offset >= 0 ? "+" : "-";
    const abs = Math.abs(offset);
    return `${isoDate(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
  }

  /* Storage -------------------------------------------------------------------------------------- */

  const KEY = "zenleaf-demo-v1";
  const FLASH_KEY = "zenleaf-demo-flash";
  let storageOk = true;
  let storageWarningShown = false;

  function storageGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { storageOk = false; return null; }
  }

  function freshDb() {
    const products = DATA.products.map((p) => Object.assign({}, p));
    return {
      version: 1,
      products,
      cart: {},
      orders: [],
      reservations: [],
      messages: [],
      subscribers: [],
      next: { product: Math.max(0, ...products.map((p) => p.id)) + 1, order: 1, reservation: 1, message: 1, subscriber: 1 },
    };
  }

  function readDb() {
    const raw = storageGet(KEY);
    if (!raw) return null;
    try {
      const data = JSON.parse(raw);
      return data && data.version === 1 && Array.isArray(data.products) && data.next ? data : null;
    } catch (e) {
      return null;
    }
  }

  function save() {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(db));
    } catch (e) {
      storageOk = false;
      showStorageProblem();
    }
  }

  let db = readDb();
  if (!db) {
    db = freshDb();
    save();
  }

  // Another tab changed the demo: pick up its data so this tab doesn't overwrite it.
  window.addEventListener("storage", (event) => {
    if (event.key !== KEY) return;
    db = readDb() || freshDb();
    setCartBadge(cartCount(), false);
  });

  /* Messages shown at the top of the next page, like Django's messages framework. */
  function flash(level, text) {
    try { window.sessionStorage.setItem(FLASH_KEY, JSON.stringify({ level, text })); } catch (e) { /* not shown */ }
  }

  function showFlash(level, text) {
    const box = $("[data-flash]");
    if (!box) return;
    const name = level === "success" ? "check" : level === "error" || level === "warning" ? "alert" : "info";
    box.insertAdjacentHTML("beforeend",
      `<div class="alert alert--${level}" role="${level === "error" ? "alert" : "status"}">${icon(name)}<p>${esc(text)}</p></div>`);
    box.hidden = false;
  }

  function showPendingFlash() {
    let raw = null;
    try {
      raw = window.sessionStorage.getItem(FLASH_KEY);
      window.sessionStorage.removeItem(FLASH_KEY);
    } catch (e) { return; }
    if (!raw) return;
    try { const f = JSON.parse(raw); showFlash(f.level, f.text); } catch (e) { /* ignore */ }
  }

  function showStorageProblem() {
    if (storageWarningShown) return;
    storageWarningShown = true;
    showFlash("warning", "This browser isn't letting the demo save anything (some private windows block it), so what you do here is lost when you leave the page.");
  }

  /* Menu data ------------------------------------------------------------------------------------ */

  const categoryBySlug = (slug) => DATA.categories.find((c) => c.slug === slug) || null;
  const categoryName = (p) => (categoryBySlug(p.category) || { name: "" }).name;
  const productById = (id) => db.products.find((p) => p.id === Number(id)) || null;
  const productBySlug = (slug) => db.products.find((p) => p.slug === slug) || null;
  const productUrl = (p) => url("menu/item/?slug=" + encodeURIComponent(p.slug));
  const illustrationSrc = (key) => `${DATA.static}img/menu/${key}.svg`;
  const illustrationAlt = (key) => (DATA.illustrations[key] || { alt: "Illustration of a drink" }).alt;

  function menuOrder(a, b) {
    const ca = categoryBySlug(a.category), cb = categoryBySlug(b.category);
    return ((ca ? ca.sort_order : 99) - (cb ? cb.sort_order : 99)) || (a.sort_order - b.sort_order) || a.name.localeCompare(b.name);
  }

  const listedProducts = () => db.products.filter((p) => p.is_listed).sort(menuOrder);
  const menuCategories = () => DATA.categories
    .filter((c) => db.products.some((p) => p.is_listed && p.category === c.slug))
    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));

  /* Cart ----------------------------------------------------------------------------------------- */

  const maxQty = CONF.max_item_quantity;
  const cartCount = () => Object.values(db.cart).reduce((sum, qty) => sum + qty, 0);

  function cartLines() {
    let changed = false;
    const lines = [];
    Object.keys(db.cart).forEach((id) => {
      const product = productById(id);
      if (!product) { delete db.cart[id]; changed = true; return; }   // deleted in the staff area
      const quantity = db.cart[id];
      const problem = !product.is_listed ? "This item is no longer on the menu."
        : !product.is_available ? "This item is sold out right now." : "";
      lines.push({ product, quantity, total: product.price * quantity, problem });
    });
    if (changed) save();
    return lines.sort((a, b) => menuOrder(a.product, b.product));
  }

  const subtotal = (lines) => lines.reduce((sum, line) => sum + line.total, 0);

  function addToCart(product, quantity) {
    if (!product || !product.is_listed) return { ok: false, message: "That item isn't on the menu any more." };
    if (!product.is_available) return { ok: false, message: `Sorry, ${product.name} is sold out right now.` };
    const before = db.cart[product.id] || 0;
    const after = Math.min(before + Math.max(quantity, 1), maxQty);
    if (after === before) {
      return { ok: false, message: `You already have the maximum of ${maxQty} × ${product.name} in your cart.` };
    }
    db.cart[product.id] = after;
    save();
    return { ok: true, message: `Added ${product.name} to your cart.` };
  }

  function setQuantity(id, quantity) {
    const qty = Math.max(0, Math.min(quantity, maxQty));
    if (qty === 0) delete db.cart[id];
    else db.cart[id] = qty;
    save();
    return qty;
  }

  function setCartBadge(count, bump) {
    if (bump) { UI.updateCartCount(count); return; }
    const badge = $("[data-cart-count]");
    const label = $("[data-cart-label]");
    if (badge) {
      badge.textContent = count;
      badge.toggleAttribute("data-empty", count === 0);
    }
    if (label) label.textContent = count + (count === 1 ? " item" : " items");
  }

  /* Shared markup --------------------------------------------------------------------------------- */

  function statusBadge(status, labels) {
    const tone = LABELS.tones[status] || "neutral";
    return `<span class="badge badge--${tone}">${esc(labels[status] || status)}</span>`;
  }

  function emptyState(iconName, title, text, link, options) {
    const opts = options || {};
    const level = opts.level || "h2";
    const button = link ? `<a class="${opts.buttonClass || "btn btn--secondary"}" href="${link.href}">${esc(link.label)}</a>` : "";
    return `<div class="empty-state${opts.page ? " empty-state--page" : ""}">${icon(iconName, "empty-state__icon")}` +
      `<${level}>${esc(title)}</${level}><p>${esc(text)}</p>${button}</div>`;
  }

  function brewMeta(p) {
    const items = [];
    if (p.caffeine) items.push(`<li>${icon("bolt")}${esc(LABELS.caffeine[p.caffeine] || "")}</li>`);
    if (p.brew_temperature_c) items.push(`<li>${icon("thermometer")}${esc(p.brew_temperature_c)}°C</li>`);
    if (p.brew_time) items.push(`<li>${icon("timer")}${esc(p.brew_time)}</li>`);
    return items.length ? `<ul class="meta-list">${items.join("")}</ul>` : "";
  }

  function productCard(p) {
    const link = productUrl(p);
    const action = p.is_available
      ? `<button class="btn btn--small" type="button" data-add="${p.id}">${icon("plus")}<span>Add<span class="visually-hidden"> ${esc(p.name)} to cart</span></span></button>`
      : `<p class="badge badge--muted">Sold out</p>`;
    return `<article class="product-card${p.is_available ? "" : " is-sold-out"}">` +
      `<a class="product-card__media" href="${link}" tabindex="-1" aria-hidden="true"><img src="${illustrationSrc(p.illustration)}" alt="" width="480" height="360" loading="lazy"></a>` +
      `<div class="product-card__body"><p class="product-card__category">${esc(categoryName(p))}</p>` +
      `<h3 class="product-card__title"><a href="${link}">${esc(p.name)}</a></h3>` +
      `<p class="product-card__desc">${esc(p.short_description)}</p>${brewMeta(p)}</div>` +
      `<div class="product-card__footer"><p class="price"><span class="visually-hidden">Price: </span>${money(p.price)}</p>${action}</div>` +
      `</article>`;
  }

  const productGrid = (products) => `<div class="product-grid">${products.map(productCard).join("")}</div>`;

  function notFound(eyebrow, title, text) {
    return `<div class="container error-page"><p class="eyebrow">${esc(eyebrow)}</p><h1>${esc(title)}</h1><p class="lede">${esc(text)}</p>` +
      `<div class="button-row"><a class="btn" href="${url("menu/")}">Browse the menu</a><a class="btn btn--secondary" href="${url()}">Go to the home page</a></div></div>`;
  }

  // Add buttons on product cards anywhere on the page.
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-add]");
    if (!button) return;
    const result = addToCart(productById(button.getAttribute("data-add")), 1);
    if (result.ok) setCartBadge(cartCount(), true);
    UI.showToast(result.message, !result.ok, result.ok);
  });

  /* Forms: validation messages shown the same way as the Django forms ------------------------------ */

  const EMAIL = /^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$/;
  const PHONE = /^[0-9+()\-\s]{6,20}$/;
  const REQUIRED = "This field is required.";

  const value = (form, name) => (form.elements[name] ? String(form.elements[name].value || "").trim() : "");

  function checkEmail(email, errors) {
    if (!email) errors.email = "Enter your email address.";
    else if (email.length > 254 || !EMAIL.test(email)) errors.email = "Enter a valid email address, like name@example.com.";
  }

  function checkPhone(phone, errors) {
    if (phone && !PHONE.test(phone)) errors.phone = "Enter a phone number using digits, spaces, +, - or brackets (6 to 20 characters).";
  }

  function clearErrors(form) {
    $all("[data-error-summary]", form).forEach((node) => node.remove());
    $all(".field--error", form).forEach((node) => node.classList.remove("field--error"));
    $all("[data-demo-error]", form).forEach((node) => node.remove());
    $all("[aria-invalid]", form).forEach((input) => {
      input.removeAttribute("aria-invalid");
      const hint = document.getElementById(input.id + "-hint");
      if (hint) input.setAttribute("aria-describedby", hint.id);
      else input.removeAttribute("aria-describedby");
    });
  }

  /* Shows errors ({field name: message}) next to the fields and in a summary that takes focus.
     Returns true when there were errors. */
  function showErrors(form, errors) {
    clearErrors(form);
    const items = [];
    Array.from(form.elements).forEach((input) => {
      const message = input.name && errors[input.name];
      if (!message || input.type === "hidden") return;
      const field = input.closest(".field");
      const label = form.querySelector(`label[for="${input.id}"]`);
      const labelText = label ? label.firstChild.textContent.trim() : input.name;
      if (field) field.classList.add("field--error");
      const error = document.createElement("p");
      error.className = "field__error";
      error.id = input.id + "-error";
      error.setAttribute("data-demo-error", "");
      error.innerHTML = `${icon("alert")}<span>${esc(message)}</span>`;
      input.before(error);
      input.setAttribute("aria-invalid", "true");
      const hint = document.getElementById(input.id + "-hint");
      input.setAttribute("aria-describedby", (hint ? hint.id + " " : "") + error.id);
      items.push(`<li><a href="#${input.id}">${esc(labelText)}: ${esc(message)}</a></li>`);
    });
    if (!items.length) return false;
    form.insertAdjacentHTML("afterbegin",
      `<div class="error-summary" role="alert" tabindex="-1" data-error-summary><h2 class="error-summary__title">${icon("alert")} Please fix the following</h2><ul>${items.join("")}</ul></div>`);
    $("[data-error-summary]", form).focus();
    return true;
  }

  const isSpam = (form) => Boolean(form.elements.website && form.elements.website.value);

  /* Footer newsletter (every public page) -------------------------------------------------------------- */

  function initNewsletter() {
    const form = $("[data-newsletter-form]");
    if (!form) return;
    const input = form.querySelector("input[type=email]");
    const status = form.querySelector("[data-newsletter-status]");
    const say = (text, ok) => {
      status.textContent = text;
      status.className = "newsletter-form__status " + (ok ? "is-success" : "is-error");
      if (ok) { input.value = ""; input.removeAttribute("aria-invalid"); }
      else { input.setAttribute("aria-invalid", "true"); input.focus(); }
    };
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const email = input.value.trim().toLowerCase();
      const errors = {};
      checkEmail(email, errors);
      if (errors.email) { say(errors.email, false); return; }
      if (isSpam(form)) { say("You're subscribed.", true); return; }
      if (db.subscribers.some((s) => s.email === email)) { say("You're already subscribed with that address.", true); return; }
      db.subscribers.push({ id: db.next.subscriber++, email, source: "footer", created: new Date().toISOString() });
      save();
      say("You're subscribed. This demo saves your address in this browser and never sends email.", true);
    });
  }

  /* Reset ------------------------------------------------------------------------------------------ */

  function initReset() {
    $all("[data-reset-confirm]").forEach((button) => {
      button.addEventListener("click", () => {
        db = freshDb();
        save();
        try { window.sessionStorage.removeItem(FLASH_KEY); } catch (e) { /* ignore */ }
        flash("success", "The demo was reset: everything it saved in this browser was cleared, and the original menu is back.");
        reload();
      });
    });
  }

  /* Home ------------------------------------------------------------------------------------------- */

  function renderHome() {
    const featured = listedProducts().filter((p) => p.is_featured).slice(0, 4);
    $("[data-featured]").innerHTML = featured.length ? productGrid(featured)
      : emptyState("leaf", "Nothing featured right now", "The full menu is still open.",
        { href: url("menu/"), label: "Browse the menu" }, { level: "h3" });

    const tiles = menuCategories().map((c) => {
      const count = listedProducts().filter((p) => p.category === c.slug).length;
      return `<li><a class="category-tile" href="${url("menu/?category=" + encodeURIComponent(c.slug))}">` +
        `<span class="category-tile__name">${esc(c.name)}</span><span class="category-tile__desc">${esc(c.description)}</span>` +
        `<span class="category-tile__count">${count} ${plural(count, "item")} ${icon("arrow-right")}</span></a></li>`;
    });
    const list = $("[data-categories]");
    list.innerHTML = tiles.join("");
    list.closest("section").hidden = !tiles.length;
  }

  /* Menu ------------------------------------------------------------------------------------------- */

  function renderMenu() {
    const q = param("q").slice(0, 60);
    const slug = param("category");
    const availableOnly = params.get("available") === "1";
    const categories = menuCategories();
    const active = categories.find((c) => c.slug === slug) || null;

    // The filter controls show the current choice, and chip links keep the other filters.
    $all(".chip-row .chip[data-category]").forEach((chip) => {
      const cat = chip.getAttribute("data-category");
      chip.hidden = Boolean(cat) && !categories.some((c) => c.slug === cat);
      const next = new URLSearchParams(params);
      if (cat) next.set("category", cat); else next.delete("category");
      next.delete("page");
      chip.setAttribute("href", "?" + next.toString());
      if ((active ? active.slug : "") === cat) chip.setAttribute("aria-current", "true");
      else chip.removeAttribute("aria-current");
    });
    const form = $("[data-menu-filters]");
    if (form) {
      form.elements.q.value = q;
      form.elements.available.checked = availableOnly;
      $all("input[type=hidden][name=category]", form).forEach((node) => node.remove());
      if (active) form.insertAdjacentHTML("afterbegin", `<input type="hidden" name="category" value="${esc(active.slug)}">`);
    }

    let products = listedProducts();
    if (active) products = products.filter((p) => p.category === active.slug);
    if (q) {
      const needle = q.toLowerCase();
      products = products.filter((p) => [p.name, p.short_description, p.tasting_notes, categoryName(p)]
        .some((text) => (text || "").toLowerCase().includes(needle)));
    }
    if (availableOnly) products = products.filter((p) => p.is_available);

    let html = "";
    if (slug && !active) {
      html += `<div class="alert alert--info" role="status">${icon("info")}<p>That category isn't on the menu, so all items are shown.</p></div>`;
    }
    if (q || active || availableOnly) {
      const summary = `${products.length} ${plural(products.length, "item")}${active ? " in " + esc(active.name) : ""}` +
        `${q ? " matching “" + esc(q) + "”" : ""}${availableOnly ? ", available now" : ""}.`;
      html += `<h2 class="visually-hidden">Matching items</h2><p class="result-count" id="result-count">${summary} <a href="${url("menu/")}">Clear filters</a></p>`;
      html += products.length ? productGrid(products)
        : emptyState("search", "Nothing matches", "Try a different word, such as “green”, “malty” or “caffeine-free”, or clear the filters.",
          { href: url("menu/"), label: "Show the whole menu" });
    } else if (!products.length) {
      html += emptyState("leaf", "The menu is empty", "No items are on the menu right now. Add some in the staff area, or reset the demo to bring back the sample menu.",
        { href: url("staff/products/"), label: "Open the staff area" });
    } else {
      categories.forEach((c) => {
        const items = products.filter((p) => p.category === c.slug);
        if (!items.length) return;
        html += `<section class="menu-section" aria-labelledby="cat-${esc(c.slug)}"><div class="menu-section__head">` +
          `<h2 id="cat-${esc(c.slug)}">${esc(c.name)}</h2><p>${esc(c.description)}</p></div>${productGrid(items)}</section>`;
      });
    }
    $("[data-menu-results]").innerHTML = html;
  }

  /* Product page ---------------------------------------------------------------------------------- */

  function renderProduct() {
    const box = $("[data-product-view]");
    const p = productBySlug(param("slug"));
    if (!p || !p.is_listed) {
      document.title = "Item not found · ZenLeaf Tea Lounge";
      box.outerHTML = notFound("Not on the menu", "We couldn't find that item", "The link may be old, or the item may have left the menu.");
      return;
    }
    document.title = `${p.name} · ZenLeaf Tea Lounge`;
    const category = categoryBySlug(p.category) || { name: "", slug: "" };
    const notes = (p.tasting_notes || "").split(",").map((n) => n.trim()).filter(Boolean);
    const shortCaffeine = { none: "None (caffeine-free)", low: "Low", medium: "Medium", high: "High" };
    const facts = [
      p.caffeine && `<div><dt>${icon("bolt")}Caffeine</dt><dd>${esc(shortCaffeine[p.caffeine] || "")}</dd></div>`,
      p.brew_temperature_c && `<div><dt>${icon("thermometer")}Water</dt><dd>${esc(p.brew_temperature_c)}°C</dd></div>`,
      p.brew_time && `<div><dt>${icon("timer")}Steep</dt><dd>${esc(p.brew_time)}</dd></div>`,
      notes.length && `<div><dt>${icon("leaf")}Tasting notes</dt><dd>${esc(notes.join(", "))}</dd></div>`,
      p.allergens && `<div><dt>${icon("info")}Allergens</dt><dd>${esc(p.allergens)}</dd></div>`,
    ].filter(Boolean).join("");
    const buy = p.is_available
      ? `<form class="add-form" novalidate data-add-form><div class="add-form__qty"><label for="qty">Quantity</label>` +
        `<input id="qty" type="number" name="quantity" value="1" min="1" max="${maxQty}" inputmode="numeric"></div>` +
        `<button class="btn btn--large" type="submit">${icon("plus")}Add to cart</button></form><p class="muted" data-in-cart></p>`
      : `<div class="alert alert--info" role="status">${icon("info")}<p>This item is sold out right now, so it can't be ordered. Other items in ${esc(category.name)} are below.</p></div>`;
    const related = listedProducts().filter((o) => o.category === p.category && o.id !== p.id).slice(0, 3);

    box.innerHTML =
      `<nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="${url("menu/")}">Menu</a></li>` +
      `<li><a href="${url("menu/?category=" + encodeURIComponent(category.slug))}">${esc(category.name)}</a></li>` +
      `<li><span aria-current="page">${esc(p.name)}</span></li></ol></nav>` +
      `<article class="product-detail"><div class="product-detail__art"><img src="${illustrationSrc(p.illustration)}" alt="${esc(illustrationAlt(p.illustration))}" width="480" height="360"></div>` +
      `<div class="product-detail__info"><p class="eyebrow">${esc(category.name)}</p><h1>${esc(p.name)}</h1>` +
      `<p class="product-detail__price">${money(p.price)} ${p.is_available ? `<span class="badge badge--success">${icon("check")}Available</span>` : `<span class="badge badge--muted">Sold out</span>`}</p>` +
      `<p class="lede">${esc(p.short_description)}</p>${p.description ? `<p>${esc(p.description)}</p>` : ""}` +
      `<dl class="facts">${facts}</dl>${buy}</div></article>` +
      (related.length ? `<section class="section section--related" aria-labelledby="related-title"><h2 id="related-title">More in ${esc(category.name)}</h2>${productGrid(related)}</section>` : "");

    const inCart = $("[data-in-cart]", box);
    const showInCart = () => {
      if (!inCart) return;
      const qty = db.cart[p.id] || 0;
      inCart.innerHTML = qty ? `You have ${qty} in your cart. <a href="${url("cart/")}">View cart</a>` : "";
    };
    showInCart();
    const form = $("[data-add-form]", box);
    if (form) {
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const qty = Math.max(1, Math.min(parseInt(form.elements.quantity.value, 10) || 1, maxQty));
        const result = addToCart(productById(p.id), qty);
        if (result.ok) setCartBadge(cartCount(), true);
        UI.showToast(result.message, !result.ok, result.ok);
        showInCart();
      });
    }
  }

  /* Cart --------------------------------------------------------------------------------------------- */

  function cartLine(line) {
    const p = line.product;
    const name = esc(p.name);
    const disabledMinus = line.problem ? " disabled" : "";
    const disabledPlus = line.quantity >= maxQty || line.problem ? " disabled" : "";
    return `<li class="cart-line${line.problem ? " cart-line--problem" : ""}" data-line="${p.id}">` +
      `<img class="cart-line__art" src="${illustrationSrc(p.illustration)}" alt="" width="96" height="72">` +
      `<div class="cart-line__info"><h3 class="cart-line__name">${p.is_listed ? `<a href="${productUrl(p)}">${name}</a>` : name}</h3>` +
      `<p class="muted">${money(p.price)} each</p>${line.problem ? `<p class="field__error">${icon("alert")}<span>${esc(line.problem)}</span></p>` : ""}</div>` +
      `<div class="qty-stepper">` +
      `<button class="icon-btn" type="button" data-cart-action="decrease" data-id="${p.id}" aria-label="Decrease quantity of ${name}"${disabledMinus}>${icon("minus")}</button>` +
      `<span class="qty-stepper__value"><span class="visually-hidden">Quantity: </span>${line.quantity}</span>` +
      `<button class="icon-btn" type="button" data-cart-action="increase" data-id="${p.id}" aria-label="Increase quantity of ${name}"${disabledPlus}>${icon("plus")}</button>` +
      `</div>` +
      `<p class="cart-line__total"><span class="visually-hidden">Line total: </span>${money(line.total)}</p>` +
      `<div class="cart-line__remove"><button class="btn btn--quiet btn--small" type="button" data-cart-action="remove" data-id="${p.id}">${icon("trash")}Remove<span class="visually-hidden"> ${name}</span></button></div>` +
      `</li>`;
  }

  function renderCart() {
    const box = $("[data-cart-view]");
    const lines = cartLines();
    if (!lines.length) {
      box.innerHTML = emptyState("bag", "Your cart is empty", "Add a tea, a latte or something to eat from the menu.",
        { href: url("menu/"), label: "Browse the menu" }, { page: true, buttonClass: "btn btn--large" });
      return;
    }
    const problems = lines.some((line) => line.problem);
    const next = problems
      ? `<p class="field__error">${icon("alert")}<span>Remove the items marked above to continue.</span></p><span class="btn btn--large btn--block is-disabled" aria-disabled="true">Continue to checkout</span>`
      : `<a class="btn btn--large btn--block" href="${url("checkout/")}">Continue to checkout ${icon("arrow-right")}</a>`;
    box.innerHTML =
      `<div class="cart-layout"><section aria-labelledby="cart-items-title"><h2 class="visually-hidden" id="cart-items-title">Items</h2>` +
      `<ul class="cart-lines">${lines.map(cartLine).join("")}</ul>` +
      `<a class="link-arrow link-arrow--back" href="${url("menu/")}">${icon("arrow-left")} Keep browsing</a></section>` +
      `<aside class="summary-card" aria-labelledby="summary-title"><h2 id="summary-title">Summary</h2>` +
      `<dl class="summary-card__rows"><div><dt>Items</dt><dd>${cartCount()}</dd></div><div class="summary-card__total"><dt>Total</dt><dd>${money(subtotal(lines))}</dd></div></dl>` +
      `<p class="muted">Payment isn't taken online. This demo saves your order in this browser, and you can follow it through the staff area.</p>${next}</aside></div>`;
  }

  function initCart() {
    renderCart();
    const box = $("[data-cart-view]");
    box.addEventListener("click", (event) => {
      const button = event.target.closest("[data-cart-action]");
      if (!button || button.disabled) return;
      const action = button.getAttribute("data-cart-action");
      const id = button.getAttribute("data-id");
      const product = productById(id);
      const current = db.cart[id] || 0;
      let announcement;
      if (action === "remove") {
        setQuantity(id, 0);
        announcement = `Removed ${product ? product.name : "the item"} from your cart.`;
      } else {
        const qty = setQuantity(id, current + (action === "increase" ? 1 : -1));
        announcement = qty ? `Quantity of ${product ? product.name : "the item"}: ${qty}.` : `Removed ${product ? product.name : "the item"} from your cart.`;
      }
      setCartBadge(cartCount(), false);
      renderCart();
      // Keep keyboard focus on the same control, or on the page heading if the line is gone.
      const same = $(`[data-cart-action="${action}"][data-id="${id}"]`, box);
      const fallback = $(`[data-line="${id}"] button:not([disabled])`, box);
      const target = same && !same.disabled ? same : fallback || $("[data-page-heading]");
      if (target) target.focus();
      const live = $("[data-cart-live]");   // outside the re-rendered area, so screen readers announce it
      if (live) live.textContent = announcement;
    });
  }

  /* Checkout ---------------------------------------------------------------------------------------- */

  function initCheckout() {
    const lines = cartLines();
    if (!lines.length) {
      flash("info", "Your cart is empty. Add something from the menu first.");
      window.location.replace(url("cart/"));
      return;
    }
    if (lines.some((line) => line.problem)) {
      flash("error", "Some items in your cart can't be ordered right now. Remove them to continue.");
      window.location.replace(url("cart/"));
      return;
    }
    const total = subtotal(lines);
    $("[data-checkout-summary]").innerHTML =
      `<ul class="summary-lines">${lines.map((l) => `<li><span>${l.quantity} × ${esc(l.product.name)}</span><span>${money(l.total)}</span></li>`).join("")}</ul>` +
      `<dl class="summary-card__rows"><div class="summary-card__total"><dt>Total</dt><dd>${money(total)}</dd></div></dl>`;
    const button = $("[data-place-order]");
    button.textContent = `Place order · ${money(total)}`;

    const form = $("[data-demo-form=checkout]");
    let placed = false;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (placed) return;
      const data = {
        customer_name: value(form, "customer_name"), email: value(form, "email"),
        phone: value(form, "phone"), notes: value(form, "notes"),
      };
      const errors = {};
      if (!data.customer_name) errors.customer_name = "Enter your name.";
      checkEmail(data.email, errors);
      checkPhone(data.phone, errors);
      if (showErrors(form, errors)) return;
      if (isSpam(form)) { db.cart = {}; save(); go(""); return; }
      const current = cartLines();   // read again, in case another tab changed the cart
      if (!current.length || current.some((line) => line.problem)) { reload(); return; }
      placed = true;
      button.disabled = true;
      const now = new Date().toISOString();
      const order = {
        number: "ZL-" + String(db.next.order++).padStart(5, "0"),
        created: now, updated: now, status: "received", staff_note: "",
        customer_name: data.customer_name, email: data.email, phone: data.phone, notes: data.notes,
        items: current.map((l) => ({ product_id: l.product.id, product_name: l.product.name, unit_price: l.product.price, quantity: l.quantity })),
        subtotal: subtotal(current), item_count: current.reduce((n, l) => n + l.quantity, 0),
      };
      db.orders.push(order);
      db.cart = {};
      save();
      flash("success", `Thank you, ${order.customer_name.split(/\s+/)[0]}. Order ${order.number} is saved.`);
      go("orders/?number=" + encodeURIComponent(order.number));
    });
  }

  /* Order status (guest) --------------------------------------------------------------------------------- */

  function renderOrder() {
    const box = $("[data-order-view]");
    const order = db.orders.find((o) => o.number === param("number"));
    if (!order) {
      document.title = "Order not found · ZenLeaf Tea Lounge";
      box.innerHTML = notFound("Order not found", "We couldn't find that order in this browser",
        "Orders in this online demo are saved in the browser they were placed in, and a reset clears them.");
      return;
    }
    document.title = `Order ${order.number} · ZenLeaf Tea Lounge`;
    const created = new Date(order.created);
    const progress = LABELS.order_progress;
    const index = progress.indexOf(order.status);
    const steps = order.status === "cancelled"
      ? `<p>This order was cancelled. If that's unexpected, <a href="${url("contact/")}">send a message</a> and mention ${esc(order.number)}.</p>`
      : `<ol class="progress" aria-label="Order progress">${progress.map((status, i) =>
        `<li class="progress__step${i < index ? " is-done" : i === index ? " is-current" : ""}"${i === index ? ' aria-current="step"' : ""}>` +
        `<span class="progress__dot">${i < index ? icon("check") : ""}</span>` +
        `<span class="progress__label">${esc(LABELS.order_status[status])}${i < index ? '<span class="visually-hidden"> (done)</span>' : ""}</span></li>`).join("")}</ol>`;
    const staffLink = url("staff/orders/view/?number=" + encodeURIComponent(order.number));
    box.innerHTML =
      `<div class="page-head page-head--compact"><div class="container"><p class="eyebrow">Order confirmation</p><h1>Order ${esc(order.number)}</h1>` +
      `<p class="lede">Placed by ${esc(order.customer_name)} on ${formatDate(created)} at ${clockOf(created)}.</p></div></div>` +
      `<div class="container status-layout"><section class="status-card" aria-labelledby="status-title">` +
      `<h2 id="status-title">Status: ${statusBadge(order.status, LABELS.order_status)}</h2>${steps}` +
      `<div class="notice">${icon("info")}<p>This order is saved in this browser. In this online demo you move it along yourself, in the <a href="${staffLink}">staff area</a>. Payment isn't taken online, and no emails or texts are sent.</p></div>` +
      `<a class="btn btn--secondary" href="${esc(window.location.pathname + window.location.search)}">Refresh status</a></section>` +
      `<aside class="summary-card" aria-labelledby="items-title"><h2 id="items-title">Items</h2><ul class="summary-lines">` +
      order.items.map((i) => `<li><span>${i.quantity} × ${esc(i.product_name)}</span><span>${money(i.unit_price * i.quantity)}</span></li>`).join("") +
      `</ul><dl class="summary-card__rows"><div class="summary-card__total"><dt>Total</dt><dd>${money(order.subtotal)}</dd></div></dl>` +
      (order.notes ? `<p><strong>Your notes:</strong> ${esc(order.notes)}</p>` : "") +
      `<a class="link-arrow" href="${url("menu/")}">Back to the menu ${icon("arrow-right")}</a></aside></div>`;
  }

  /* Table requests ---------------------------------------------------------------------------------------- */

  function validateReservation(form) {
    const v = {
      date: value(form, "date"), time: value(form, "time"), party_size: value(form, "party_size"),
      name: value(form, "name"), email: value(form, "email"), phone: value(form, "phone"), notes: value(form, "notes"),
    };
    const errors = {};
    const today = startOfToday();
    const days = CONF.booking_days_ahead;
    if (!v.date) errors.date = "Choose a date.";
    else {
      const d = parseDate(v.date);
      if (!d) errors.date = "Enter a date like 2026-10-05.";
      else if (d < today) errors.date = "Choose today or a later date.";
      else if (d > addDays(today, days)) errors.date = `Requests can be made up to ${days} days ahead.`;
    }
    if (!v.time) errors.time = "Choose a time.";
    else if (!CONF.slots.includes(v.time)) errors.time = "Choose one of the listed times.";
    const party = Number(v.party_size);
    if (!v.party_size) errors.party_size = "Choose a party size.";
    else if (!Number.isInteger(party) || party < 1 || party > CONF.max_party_size) errors.party_size = "Choose one of the listed party sizes.";
    if (!v.name) errors.name = "Enter your name.";
    checkEmail(v.email, errors);
    checkPhone(v.phone, errors);
    if (!errors.date && !errors.time && v.date === isoDate(today)) {
      const notice = CONF.min_notice_minutes;
      if (slotDate(v.date, v.time) < new Date(Date.now() + notice * 60000)) {
        errors.time = `For today, choose a time at least ${notice} minutes from now.`;
      }
    }
    return { values: v, errors };
  }

  function initReserve() {
    const form = $("#main form.form-card");
    const today = startOfToday();
    form.elements.date.min = isoDate(today);
    form.elements.date.max = isoDate(addDays(today, CONF.booking_days_ahead));
    const party = param("party");
    if (party && form.elements.party_size.querySelector(`option[value="${CSS.escape(party)}"]`)) form.elements.party_size.value = party;

    let sent = false;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (sent) return;
      const { values: v, errors } = validateReservation(form);
      if (showErrors(form, errors)) return;
      if (isSpam(form)) { go(""); return; }
      sent = true;
      const now = new Date().toISOString();
      const reservation = {
        reference: "R-" + String(db.next.reservation++).padStart(5, "0"),
        created: now, updated: now, status: "pending", guest_message: "",
        name: v.name, email: v.email, phone: v.phone, date: v.date, time: v.time,
        party_size: Number(v.party_size), notes: v.notes,
      };
      db.reservations.push(reservation);
      save();
      flash("success", `Request ${reservation.reference} received. It's pending until a member of staff confirms it.`);
      go("reservations/?ref=" + encodeURIComponent(reservation.reference));
    });
  }

  const isActive = (r) => r.status === "pending" || r.status === "confirmed";
  const canCancel = (r) => isActive(r) && slotDate(r.date, r.time) > new Date();

  function renderReservation() {
    const box = $("[data-reservation-view]");
    const r = db.reservations.find((x) => x.reference === param("ref"));
    if (!r) {
      document.title = "Table request not found · ZenLeaf Tea Lounge";
      box.innerHTML = notFound("Request not found", "We couldn't find that table request in this browser",
        "Table requests in this online demo are saved in the browser they were made in, and a reset clears them.");
      return;
    }
    document.title = `Table request ${r.reference} · ZenLeaf Tea Lounge`;
    const said = {
      pending: "Your request is waiting for a member of staff to confirm it. Check back on this page for updates.",
      confirmed: "Your table is confirmed.",
      declined: "Sorry, this request was declined.",
      cancelled: "This request was cancelled.",
    };
    const staffLink = url("staff/reservations/view/?ref=" + encodeURIComponent(r.reference));
    const cancel = canCancel(r)
      ? `<details class="confirm-details"><summary class="btn btn--quiet">Cancel this request</summary>` +
        `<div class="confirm-details__panel"><p>Cancel request ${esc(r.reference)}? This can't be undone.</p>` +
        `<button class="btn btn--danger" type="button" data-cancel-request>Yes, cancel it</button></div></details>`
      : "";
    box.innerHTML =
      `<div class="page-head page-head--compact"><div class="container"><p class="eyebrow">Table request</p><h1>Request ${esc(r.reference)}</h1></div></div>` +
      `<div class="container status-layout"><section class="status-card" aria-labelledby="res-status-title">` +
      `<h2 id="res-status-title">Status: ${statusBadge(r.status, LABELS.reservation_status)}</h2><p>${said[r.status] || ""}</p>` +
      (r.guest_message ? `<blockquote class="staff-note"><p>${esc(r.guest_message)}</p><footer>Note from staff</footer></blockquote>` : "") +
      `<dl class="facts facts--grid">` +
      `<div><dt>${icon("calendar")}Date</dt><dd>${formatDate(parseDate(r.date), "long")}</dd></div>` +
      `<div><dt>${icon("clock")}Time</dt><dd>${slotClock(r.time)}</dd></div>` +
      `<div><dt>${icon("users")}Party</dt><dd>${r.party_size} ${plural(r.party_size, "person", "people")}</dd></div>` +
      `<div><dt>${icon("user")}Name</dt><dd>${esc(r.name)}</dd></div></dl>` +
      `<div class="notice">${icon("info")}<p>This request is saved in this browser. In this online demo you confirm or decline it yourself, in the <a href="${staffLink}">staff area</a>. No emails or texts are sent.</p></div>` +
      `<div class="button-row"><a class="btn btn--secondary" href="${esc(window.location.pathname + window.location.search)}">Refresh status</a>${cancel}</div></section>` +
      `<aside class="side-note"><h2>Need to change something?</h2><p>Cancel this request and send a new one, or <a href="${url("contact/")}">send a message</a> with your reference, ${esc(r.reference)}.</p></aside></div>`;

    const button = $("[data-cancel-request]", box);
    if (button) {
      button.addEventListener("click", () => {
        if (canCancel(r)) {
          r.status = "cancelled";
          r.updated = new Date().toISOString();
          save();
          flash("success", `Request ${r.reference} is cancelled.`);
        } else {
          flash("info", "This request can't be cancelled any more, so nothing changed.");
        }
        reload();
      });
    }
  }

  /* Contact ------------------------------------------------------------------------------------------ */

  const fingerprint = (email, message) => email.toLowerCase() + "\n" + message.toLowerCase().split(/\s+/).filter(Boolean).join(" ");

  function initContact() {
    const form = $("#main form.form-card");
    const topic = param("topic");
    if (topic && LABELS.topics[topic]) form.elements.topic.value = topic;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const v = { name: value(form, "name"), email: value(form, "email"), topic: value(form, "topic"), message: value(form, "message") };
      const errors = {};
      if (!v.name) errors.name = "Enter your name.";
      checkEmail(v.email, errors);
      if (!LABELS.topics[v.topic]) errors.topic = "Select a valid choice. That choice is not one of the available choices.";
      if (!v.message) errors.message = "Write your message.";
      else if (v.message.length < 10) errors.message = "Write at least 10 characters so we know how to help.";
      else if (v.message.length > 2000) errors.message = "Keep the message under 2,000 characters.";
      if (showErrors(form, errors)) return;
      if (isSpam(form)) { go("contact/"); return; }
      const print = fingerprint(v.email, v.message);
      const dayAgo = Date.now() - 24 * 3600 * 1000;
      if (db.messages.some((m) => m.fingerprint === print && new Date(m.created).getTime() >= dayAgo)) {
        flash("info", "We already have this message from you, so it wasn't saved twice.");
      } else {
        db.messages.push({
          id: db.next.message++, created: new Date().toISOString(), name: v.name, email: v.email,
          topic: v.topic, message: v.message, fingerprint: print, is_handled: false, read_at: null,
        });
        save();
        flash("success", "Thanks, your message is saved. You can read it in the staff area.");
      }
      go("contact/");
    });
  }

  /* Staff: counts in the navigation ----------------------------------------------------------------------- */

  const todayIso = () => isoDate(new Date());
  const upcomingPending = () => db.reservations.filter((r) => r.status === "pending" && r.date >= todayIso());

  function renderStaffCounts() {
    const counts = {
      orders: db.orders.filter((o) => o.status === "received").length,
      reservations: upcomingPending().length,
      messages: db.messages.filter((m) => !m.is_handled).length,
    };
    $all("[data-staff-count]").forEach((pill) => {
      const n = counts[pill.getAttribute("data-staff-count")] || 0;
      pill.hidden = !n;
      pill.innerHTML = n ? `${n}<span class="visually-hidden">${esc(pill.getAttribute("data-suffix") || "")}</span>` : "";
    });
  }

  const staffOrderUrl = (o) => url("staff/orders/view/?number=" + encodeURIComponent(o.number));
  const staffReservationUrl = (r) => url("staff/reservations/view/?ref=" + encodeURIComponent(r.reference));
  const byNewest = (a, b) => (a.created < b.created ? 1 : a.created > b.created ? -1 : 0);
  const bySlot = (a, b) => (a.date + a.time).localeCompare(b.date + b.time);

  function staffTitle(text) { document.title = `${text} · ZenLeaf staff`; }

  /* Staff: dashboard -------------------------------------------------------------------------------------- */

  function renderDashboard() {
    const today = todayIso();
    const newOrders = db.orders.filter((o) => o.status === "received").length;
    const openOrders = db.orders.filter((o) => ["received", "preparing", "ready"].includes(o.status)).length;
    const pending = upcomingPending();
    const todays = db.reservations.filter((r) => r.date === today && isActive(r)).length;
    const toHandle = db.messages.filter((m) => !m.is_handled).length;
    const soldOut = db.products.filter((p) => p.is_listed && !p.is_available).length;
    const stat = (href, n, label, hint) =>
      `<li><a class="stat" href="${href}"><span class="stat__value">${n}</span><span class="stat__label">${esc(label)}</span><span class="stat__hint">${esc(hint)}</span></a></li>`;
    $("[data-stats]").innerHTML =
      stat(url("staff/orders/?status=received"), newOrders, plural(newOrders, "New order"), `${openOrders} open in total`) +
      stat(url("staff/reservations/"), pending.length, plural(pending.length, "Pending table request"), `${todays} for today`) +
      stat(url("staff/messages/"), toHandle, `${plural(toHandle, "Message")} to handle`, "From the contact form") +
      stat(url("staff/products/?state=sold-out"), soldOut, plural(soldOut, "Sold-out item"), "Shown on the menu, can't be ordered");

    const recent = db.orders.slice().sort(byNewest).slice(0, 5);
    $("[data-recent-orders]").innerHTML = recent.length
      ? `<ul class="row-list">${recent.map((o) => `<li><a href="${staffOrderUrl(o)}"><span><strong>${esc(o.number)}</strong> · ${esc(o.customer_name)}</span>${statusBadge(o.status, LABELS.order_status)}</a></li>`).join("")}</ul>`
      : `<p class="empty-inline">No orders yet. They appear here when a guest checks out.</p>`;

    const next = pending.slice().sort(bySlot).slice(0, 5);
    $("[data-pending-reservations]").innerHTML = next.length
      ? `<ul class="row-list">${next.map((r) => `<li><a href="${staffReservationUrl(r)}"><span><strong>${esc(r.reference)}</strong> · ${esc(r.name)}, ${r.party_size} ${plural(r.party_size, "person", "people")}</span><span>${formatDate(parseDate(r.date), "weekday-short")}, ${slotClock(r.time)}</span></a></li>`).join("")}</ul>`
      : `<p class="empty-inline">No pending requests for today or later.</p>`;
  }

  /* Staff: products ----------------------------------------------------------------------------------------- */

  const PRODUCT_STATES = {
    all: () => true,
    listed: (p) => p.is_listed,
    "sold-out": (p) => p.is_listed && !p.is_available,
    hidden: (p) => !p.is_listed,
    featured: (p) => p.is_featured,
  };
  const TOGGLES = {
    is_available: ["available to order", "sold out"],
    is_listed: ["shown on the menu", "hidden from the menu"],
    is_featured: ["featured", "not featured"],
  };

  function toggleButton(p, field, on, off) {
    const value = Boolean(p[field]);
    return `<button type="button" class="switch" role="switch" aria-checked="${value}" data-toggle="${field}" data-id="${p.id}" data-on="${esc(on)}" data-off="${esc(off)}">` +
      `<span class="switch__track" aria-hidden="true"><span class="switch__thumb"></span></span>` +
      `<span class="switch__label">${esc(value ? on : off)}</span><span class="visually-hidden"> for ${esc(p.name)}</span></button>`;
  }

  function renderStaffProducts() {
    const q = param("q").slice(0, 60);
    const state = PRODUCT_STATES[param("state")] ? param("state") : "all";
    const category = param("category");
    const form = $("#main form.filter-bar");
    form.elements.q.value = q;
    form.elements.state.value = state;
    form.elements.category.value = categoryBySlug(category) ? category : "";

    let products = db.products.slice().sort(menuOrder).filter(PRODUCT_STATES[state]);
    if (q) {
      const needle = q.toLowerCase();
      products = products.filter((p) => p.name.toLowerCase().includes(needle) || p.short_description.toLowerCase().includes(needle));
    }
    if (category) products = products.filter((p) => p.category === category);

    const box = $("[data-products-table]");
    if (!products.length) {
      const unfiltered = !q && state === "all" && !category;
      box.innerHTML = emptyState("search", "No products match", `Try a different filter${unfiltered ? ", or add the first product" : ""}.`,
        { href: url("staff/products/"), label: "Clear filters" });
      return;
    }
    box.innerHTML =
      `<table class="data-table"><caption class="visually-hidden">Products, ${products.length} in total</caption>` +
      `<thead><tr><th scope="col">Product</th><th scope="col">Price</th><th scope="col">On menu</th><th scope="col">Available</th><th scope="col">Featured</th><th scope="col"><span class="visually-hidden">Actions</span></th></tr></thead><tbody>` +
      products.map((p) => {
        const edit = url("staff/products/edit/?id=" + p.id);
        return `<tr><td data-label="Product"><div class="product-cell"><img src="${illustrationSrc(p.illustration)}" alt="" width="64" height="48">` +
          `<div><a href="${edit}"><strong>${esc(p.name)}</strong></a><br><span class="muted small">${esc(categoryName(p))}</span></div></div></td>` +
          `<td data-label="Price">${money(p.price)}</td>` +
          `<td data-label="On menu">${toggleButton(p, "is_listed", "On menu", "Hidden")}</td>` +
          `<td data-label="Available">${toggleButton(p, "is_available", "Available", "Sold out")}</td>` +
          `<td data-label="Featured">${toggleButton(p, "is_featured", "Featured", "Not featured")}</td>` +
          `<td data-label="Actions"><a class="btn btn--quiet btn--small" href="${edit}">${icon("edit")}Edit<span class="visually-hidden"> ${esc(p.name)}</span></a></td></tr>`;
      }).join("") +
      `</tbody></table>`;

    box.addEventListener("click", (event) => {
      const button = event.target.closest("[data-toggle]");
      if (!button) return;
      const field = button.getAttribute("data-toggle");
      const product = productById(button.getAttribute("data-id"));
      if (!product || !TOGGLES[field]) return;
      product[field] = !product[field];
      save();
      button.setAttribute("aria-checked", String(product[field]));
      $(".switch__label", button).textContent = product[field] ? button.getAttribute("data-on") : button.getAttribute("data-off");
      const [on, off] = TOGGLES[field];
      UI.showToast(`${product.name} is now ${product[field] ? on : off}.`, false, false);
    });
  }

  function slugify(text) {
    return text.normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^\x00-\x7f]/g, "")
      .toLowerCase().replace(/[^\w\s-]/g, "").replace(/[-\s]+/g, "-").replace(/^[-_]+|[-_]+$/g, "");
  }

  function readNumber(raw, errors, field, options) {
    if (raw === "") {
      if (options.required) errors[field] = REQUIRED;
      return null;
    }
    const number = Number(raw);
    if (!Number.isFinite(number) || (options.integer && !Number.isInteger(number))) {
      errors[field] = options.integer ? "Enter a whole number." : "Enter a number.";
      return null;
    }
    if (options.min != null && number < options.min) errors[field] = `Ensure this value is greater than or equal to ${options.minLabel || options.min}.`;
    else if (options.max != null && number > options.max) errors[field] = `Ensure this value is less than or equal to ${options.max}.`;
    return number;
  }

  function initProductForm(editing) {
    const form = $("[data-demo-form=product]");
    let product = null;
    if (editing) {
      product = productById(param("id"));
      if (!product) {
        form.hidden = true;
        $("[data-product-missing]").hidden = false;
        staffTitle("Product not found");
        return;
      }
      const e = form.elements;
      e.name.value = product.name;
      e.slug.value = product.slug;
      e.category.value = product.category;
      e.price.value = Number(product.price).toFixed(2);
      e.sort_order.value = product.sort_order;
      e.short_description.value = product.short_description;
      e.description.value = product.description || "";
      e.illustration.value = product.illustration;
      e.caffeine.value = product.caffeine || "";
      e.brew_temperature_c.value = product.brew_temperature_c == null ? "" : product.brew_temperature_c;
      e.brew_time.value = product.brew_time || "";
      e.tasting_notes.value = product.tasting_notes || "";
      e.allergens.value = product.allergens || "";
      e.is_listed.checked = product.is_listed;
      e.is_available.checked = product.is_available;
      e.is_featured.checked = product.is_featured;
      $("[data-product-heading]").textContent = `Edit ${product.name}`;
      $("[data-product-crumb]").textContent = product.name;
      staffTitle(`Edit ${product.name}`);
      const onMenu = $("[data-view-on-menu]");
      if (product.is_listed) { onMenu.href = productUrl(product); onMenu.hidden = false; }
      $("[data-delete-link]").href = url("staff/products/delete/?id=" + product.id);
      const preview = $("[data-illustration-preview]");
      preview.src = illustrationSrc(product.illustration);
      preview.hidden = false;
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const e = form.elements;
      const errors = {};
      const name = value(form, "name");
      if (!name) errors.name = REQUIRED;
      const category = value(form, "category");
      if (!categoryBySlug(category)) errors.category = REQUIRED;
      const price = readNumber(value(form, "price"), errors, "price", { required: true, min: 1, minLabel: "1.00", max: 999999.99 });
      if (price != null && !errors.price && Math.round(price * 100) !== price * 100) errors.price = "Ensure that there are no more than 2 decimal places.";
      const sortOrder = readNumber(value(form, "sort_order"), errors, "sort_order", { required: true, integer: true, min: 0, max: 32767 });
      let slug = value(form, "slug");
      if (slug && !/^[-a-zA-Z0-9_]+$/.test(slug)) errors.slug = "Enter a valid “slug” consisting of letters, numbers, underscores or hyphens.";
      else {
        slug = slug || slugify(name);
        if (!slug) errors.slug = "Enter a name or a web address slug.";
        else if (db.products.some((p) => p.slug === slug && (!product || p.id !== product.id))) errors.slug = "Another product already uses this slug.";
      }
      if (!value(form, "short_description")) errors.short_description = REQUIRED;
      if (!DATA.illustrations[value(form, "illustration")]) errors.illustration = REQUIRED;
      const temperature = readNumber(value(form, "brew_temperature_c"), errors, "brew_temperature_c", { integer: true, min: 40, max: 100 });
      if (showErrors(form, errors)) return;

      const values = {
        name, slug, category, price, sort_order: sortOrder,
        short_description: value(form, "short_description"), description: value(form, "description"),
        illustration: value(form, "illustration"), caffeine: value(form, "caffeine"),
        brew_temperature_c: temperature, brew_time: value(form, "brew_time"),
        tasting_notes: value(form, "tasting_notes"), allergens: value(form, "allergens"),
        is_listed: e.is_listed.checked, is_available: e.is_available.checked, is_featured: e.is_featured.checked,
      };
      if (product) Object.assign(product, values);
      else db.products.push(Object.assign({ id: db.next.product++ }, values));
      save();
      flash("success", `Saved ${name}.`);
      go("staff/products/");
    });
  }

  function renderProductDelete() {
    const box = $("[data-delete-view]");
    const p = productById(param("id"));
    if (!p) {
      staffTitle("Product not found");
      box.innerHTML = `<h1>This product isn't in the demo</h1><p>It may have been deleted already, or the demo was reset.</p>` +
        `<a class="btn btn--secondary" href="${url("staff/products/")}">Back to products</a>`;
      return;
    }
    staffTitle(`Delete ${p.name}`);
    const edit = url("staff/products/edit/?id=" + p.id);
    const ordered = db.orders.reduce((n, o) => n + o.items.filter((i) => i.product_id === p.id).length, 0);
    box.innerHTML = `<h1>Delete ${esc(p.name)}?</h1>` +
      (ordered
        ? `<p>This product appears in ${ordered} past order ${plural(ordered, "line")}. Those orders keep its name and price, but they'll no longer link to it.</p>` +
          `<p>To take it off the menu without losing it, <a href="${edit}">hide it instead</a>.</p>`
        : `<p>It hasn't been ordered yet. Deleting it can't be undone.</p>`) +
      `<div class="form-actions"><button class="btn btn--danger" type="button" data-delete-confirm>${icon("trash")}Delete ${esc(p.name)}</button>` +
      `<a class="btn btn--secondary" href="${edit}">Keep it</a></div>`;
    $("[data-delete-confirm]", box).addEventListener("click", () => {
      db.products = db.products.filter((x) => x.id !== p.id);
      db.orders.forEach((o) => o.items.forEach((i) => { if (i.product_id === p.id) i.product_id = null; }));
      delete db.cart[p.id];
      save();
      flash("success", `Deleted ${p.name}. Past orders keep its name and price.`);
      go("staff/products/");
    });
  }

  /* Staff: orders -------------------------------------------------------------------------------------------- */

  const ORDER_FILTERS = {
    open: (o) => ["received", "preparing", "ready"].includes(o.status),
    received: (o) => o.status === "received",
    preparing: (o) => o.status === "preparing",
    ready: (o) => o.status === "ready",
    completed: (o) => o.status === "completed",
    cancelled: (o) => o.status === "cancelled",
    all: () => true,
  };

  function renderStaffOrders() {
    const status = ORDER_FILTERS[param("status")] ? param("status") : "open";
    const q = param("q").slice(0, 60);
    $all(".chip[data-status]").forEach((chip) => {
      const key = chip.getAttribute("data-status");
      chip.setAttribute("href", `?status=${key}${q ? "&q=" + encodeURIComponent(q) : ""}`);
      if (key === status) chip.setAttribute("aria-current", "true"); else chip.removeAttribute("aria-current");
    });
    $("[data-status-input]").value = status;
    $("#order-q").value = q;

    let orders = db.orders.filter(ORDER_FILTERS[status]).sort(byNewest);
    if (q) {
      const needle = q.toLowerCase();
      orders = orders.filter((o) => [o.number, o.customer_name, o.email].some((t) => t.toLowerCase().includes(needle)));
    }
    const box = $("[data-orders-table]");
    if (!orders.length) {
      box.innerHTML = emptyState("bag", "No orders here", q ? `Nothing matches “${q}”.` : "Orders appear when a guest checks out from the cart.",
        status !== "all" || q ? { href: "?status=all", label: "Show all orders" } : null);
      return;
    }
    box.innerHTML = `<table class="data-table"><caption class="visually-hidden">Orders</caption>` +
      `<thead><tr><th scope="col">Order</th><th scope="col">Placed</th><th scope="col">Guest</th><th scope="col">Items</th><th scope="col">Total</th><th scope="col">Status</th></tr></thead><tbody>` +
      orders.map((o) => {
        const placed = new Date(o.created);
        return `<tr><td data-label="Order"><a href="${staffOrderUrl(o)}"><strong>${esc(o.number)}</strong></a></td>` +
          `<td data-label="Placed">${formatDate(placed, "short")}, ${clockOf(placed)}</td><td data-label="Guest">${esc(o.customer_name)}</td>` +
          `<td data-label="Items">${o.item_count}</td><td data-label="Total">${money(o.subtotal)}</td>` +
          `<td data-label="Status">${statusBadge(o.status, LABELS.order_status)}</td></tr>`;
      }).join("") + `</tbody></table>`;
  }

  function showFound(found) {
    $("[data-missing]").hidden = found;
    $("[data-found]").hidden = !found;
  }

  function renderStaffOrder() {
    const order = db.orders.find((o) => o.number === param("number"));
    if (!order) { showFound(false); staffTitle("Order not found"); return; }
    showFound(true);
    staffTitle(`Order ${order.number}`);
    const created = new Date(order.created), updated = new Date(order.updated);
    $("[data-crumb]").textContent = order.number;
    $("[data-heading]").innerHTML = `Order ${esc(order.number)} ${statusBadge(order.status, LABELS.order_status)}`;
    $("[data-subheading]").textContent = `Placed ${formatDate(created, "full")} at ${clockOf(created)} · last updated ${formatDate(updated, "short")}, ${clockOf(updated)}`;
    $("[data-guest-link]").href = url("orders/?number=" + encodeURIComponent(order.number));
    $("[data-items]").innerHTML = `<table class="data-table data-table--plain"><caption class="visually-hidden">Items in order ${esc(order.number)}</caption>` +
      `<thead><tr><th scope="col">Item</th><th scope="col">Qty</th><th scope="col">Price</th><th scope="col">Line total</th></tr></thead><tbody>` +
      order.items.map((i) => `<tr><td data-label="Item">${esc(i.product_name)}</td><td data-label="Qty">${i.quantity}</td><td data-label="Price">${money(i.unit_price)}</td><td data-label="Line total">${money(i.unit_price * i.quantity)}</td></tr>`).join("") +
      `</tbody><tfoot><tr><th scope="row" colspan="3">Total</th><td data-label="Total"><strong>${money(order.subtotal)}</strong></td></tr></tfoot></table>`;
    $("[data-guest]").innerHTML =
      `<div><dt>Name</dt><dd>${esc(order.customer_name)}</dd></div><div><dt>Email</dt><dd>${esc(order.email)}</dd></div>` +
      `<div><dt>Phone</dt><dd>${esc(order.phone || "Not given")}</dd></div><div><dt>Notes</dt><dd>${esc(order.notes || "None")}</dd></div>`;

    const form = $("[data-demo-form=order-update]");
    form.elements.status.value = order.status;
    form.elements.staff_note.value = order.staff_note || "";
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const status = value(form, "status");
      if (showErrors(form, LABELS.order_status[status] ? {} : { status: REQUIRED })) return;
      order.status = status;
      order.staff_note = value(form, "staff_note");
      order.updated = new Date().toISOString();
      save();
      flash("success", `Order ${order.number} updated: ${LABELS.order_status[status]}.`);
      reload();
    });
  }

  /* Staff: table requests -------------------------------------------------------------------------------------- */

  function renderStaffReservations() {
    const statuses = Object.keys(LABELS.reservation_status);
    const status = param("status") === "all" || statuses.includes(param("status")) ? param("status") : "pending";
    const when = ["upcoming", "past", "all"].includes(param("when")) ? param("when") : "upcoming";
    $("#res-status").value = status;
    $("#res-when").value = when;
    const today = todayIso();
    let list = db.reservations.filter((r) => status === "all" || r.status === status);
    if (when === "upcoming") list = list.filter((r) => r.date >= today).sort(bySlot);
    else if (when === "past") list = list.filter((r) => r.date < today).sort((a, b) => bySlot(b, a));
    else list = list.sort(bySlot);

    const box = $("[data-reservations-table]");
    if (!list.length) {
      box.innerHTML = emptyState("calendar", "No table requests here", "Try another status or date filter. New requests arrive as pending.",
        { href: "?status=all&when=all", label: "Show every request" });
      return;
    }
    box.innerHTML = `<table class="data-table"><caption class="visually-hidden">Table requests</caption>` +
      `<thead><tr><th scope="col">Request</th><th scope="col">Date and time</th><th scope="col">Guest</th><th scope="col">Party</th><th scope="col">Status</th></tr></thead><tbody>` +
      list.map((r) => `<tr><td data-label="Request"><a href="${staffReservationUrl(r)}"><strong>${esc(r.reference)}</strong></a></td>` +
        `<td data-label="Date and time">${formatDate(parseDate(r.date), "weekday")}, ${slotClock(r.time)}</td><td data-label="Guest">${esc(r.name)}</td>` +
        `<td data-label="Party">${r.party_size}</td><td data-label="Status">${statusBadge(r.status, LABELS.reservation_status)}</td></tr>`).join("") +
      `</tbody></table>`;
  }

  function renderStaffReservation() {
    const r = db.reservations.find((x) => x.reference === param("ref"));
    if (!r) { showFound(false); staffTitle("Table request not found"); return; }
    showFound(true);
    staffTitle(`Request ${r.reference}`);
    const created = new Date(r.created);
    $("[data-crumb]").textContent = r.reference;
    $("[data-heading]").innerHTML = `Request ${esc(r.reference)} ${statusBadge(r.status, LABELS.reservation_status)}`;
    $("[data-subheading]").textContent = `Received ${formatDate(created)} at ${clockOf(created)}`;
    $("[data-guest-link]").href = url("reservations/?ref=" + encodeURIComponent(r.reference));
    $("[data-details]").innerHTML =
      `<div><dt>Date</dt><dd>${formatDate(parseDate(r.date), "long")}</dd></div><div><dt>Time</dt><dd>${slotClock(r.time)}</dd></div>` +
      `<div><dt>Party</dt><dd>${r.party_size} ${plural(r.party_size, "person", "people")}</dd></div><div><dt>Name</dt><dd>${esc(r.name)}</dd></div>` +
      `<div><dt>Email</dt><dd>${esc(r.email)}</dd></div><div><dt>Phone</dt><dd>${esc(r.phone || "Not given")}</dd></div>` +
      `<div><dt>Notes</dt><dd>${esc(r.notes || "None")}</dd></div>`;

    const form = $("[data-demo-form=reservation-update]");
    form.elements.status.value = r.status;
    form.elements.guest_message.value = r.guest_message || "";
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const status = value(form, "status");
      if (showErrors(form, LABELS.reservation_status[status] ? {} : { status: REQUIRED })) return;
      r.status = status;
      r.guest_message = value(form, "guest_message");
      r.updated = new Date().toISOString();
      save();
      flash("success", `Request ${r.reference} updated: ${LABELS.reservation_status[status]}.`);
      reload();
    });
  }

  /* Staff: messages ------------------------------------------------------------------------------------------ */

  const MESSAGE_FILTERS = { new: (m) => !m.is_handled, handled: (m) => m.is_handled, all: () => true };

  function renderStaffMessages() {
    const state = MESSAGE_FILTERS[param("state")] ? param("state") : "new";
    $all(".chip[data-state]").forEach((chip) => {
      if (chip.getAttribute("data-state") === state) chip.setAttribute("aria-current", "true"); else chip.removeAttribute("aria-current");
    });
    const list = db.messages.filter(MESSAGE_FILTERS[state]).sort(byNewest);
    const box = $("[data-messages-list]");
    if (!list.length) {
      box.innerHTML = emptyState("mail", "No messages here", state === "new" ? "Everything is handled." : "Messages from the contact form appear here.",
        state !== "all" ? { href: "?state=all", label: "Show all messages" } : null);
      return;
    }
    const preview = (text) => (text.length > 140 ? text.slice(0, 139) + "…" : text);
    box.innerHTML = `<ul class="message-list">` + list.map((m) => {
      const created = new Date(m.created);
      return `<li class="message-item${m.read_at ? "" : " is-unread"}"><a href="${url("staff/messages/view/?id=" + m.id)}">` +
        `<span class="message-item__top"><strong>${esc(m.name)}</strong><span class="muted small">${formatDate(created, "short")}, ${clockOf(created)}</span></span>` +
        `<span class="message-item__meta">${esc(LABELS.topics[m.topic] || m.topic)}${m.read_at ? "" : ' · <span class="badge badge--info">New</span>'}${m.is_handled ? ' · <span class="badge badge--success">Handled</span>' : ""}</span>` +
        `<span class="message-item__preview">${esc(preview(m.message))}</span></a></li>`;
    }).join("") + `</ul>`;
  }

  function paragraphs(text) {
    return text.split(/\n{2,}/).map((p) => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`).join("");
  }

  function renderStaffMessage() {
    const box = $("[data-message-view]");
    const m = db.messages.find((x) => x.id === Number(param("id")));
    if (!m) {
      staffTitle("Message not found");
      box.innerHTML = emptyState("mail", "This message isn't in the demo",
        "Messages are saved in the browser they were sent from. It may also have been cleared by a reset.",
        { href: url("staff/messages/?state=all"), label: "Show all messages" }, { level: "h1" });
      return;
    }
    if (!m.read_at) { m.read_at = new Date().toISOString(); save(); renderStaffCounts(); }
    staffTitle(`Message from ${m.name}`);
    $("[data-crumb]").textContent = m.name;
    const created = new Date(m.created);
    box.innerHTML = `<article class="panel message-detail"><h1>${esc(LABELS.topics[m.topic] || m.topic)}</h1>` +
      `<dl class="facts facts--inline"><div><dt>From</dt><dd>${esc(m.name)}</dd></div><div><dt>Email</dt><dd>${esc(m.email)}</dd></div>` +
      `<div><dt>Received</dt><dd>${formatDate(created)} at ${clockOf(created)}</dd></div><div><dt>Status</dt><dd>${m.is_handled ? "Handled" : "To handle"}</dd></div></dl>` +
      `<div class="message-detail__body">${paragraphs(m.message)}</div>` +
      `<div class="form-actions"><button class="btn" type="button" data-toggle-handled>${m.is_handled ? "Move back to “to handle”" : icon("check") + "Mark as handled"}</button>` +
      `<a class="btn btn--secondary" href="${url("staff/messages/")}">Back to messages</a></div>` +
      `<p class="muted small">This demo can't send replies.</p></article>`;
    $("[data-toggle-handled]", box).addEventListener("click", () => {
      m.is_handled = !m.is_handled;
      save();
      flash("success", m.is_handled ? "Marked as handled." : "Moved back to the to-handle list.");
      reload();
    });
  }

  /* Staff: newsletter subscribers ------------------------------------------------------------------------------ */

  const csvCell = (text) => {
    const cell = /^[=+\-@\t\r]/.test(text) ? "'" + text : text;
    return /[",\n\r]/.test(cell) ? `"${cell.replace(/"/g, '""')}"` : cell;
  };

  function renderSubscribers() {
    const list = db.subscribers.slice().sort(byNewest);
    const n = list.length;
    $("[data-subscriber-total]").textContent = `${n} ${plural(n, "address", "addresses")}. This demo never sends email.`;
    const exportButton = $("[data-export]");
    exportButton.hidden = !n;
    exportButton.onclick = () => {
      const rows = [["email", "source", "subscribed_at"]].concat(
        db.subscribers.slice().sort((a, b) => -byNewest(a, b)).map((s) => [s.email, s.source, localIso(new Date(s.created))]));
      const csv = rows.map((row) => row.map((cell) => csvCell(String(cell))).join(",")).join("\r\n") + "\r\n";
      const link = document.createElement("a");
      link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      link.download = `zenleaf-subscribers-${isoDate(new Date()).replace(/-/g, "")}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    };

    const box = $("[data-subscribers-table]");
    if (!n) {
      box.innerHTML = emptyState("mail", "No subscribers yet", "Sign-ups from the newsletter form in the site footer appear here.");
      return;
    }
    box.innerHTML = `<table class="data-table"><caption class="visually-hidden">Newsletter subscribers</caption>` +
      `<thead><tr><th scope="col">Email</th><th scope="col">Signed up</th><th scope="col">From</th><th scope="col"><span class="visually-hidden">Actions</span></th></tr></thead><tbody>` +
      list.map((s) => {
        const created = new Date(s.created);
        return `<tr><td data-label="Email">${esc(s.email)}</td><td data-label="Signed up">${formatDate(created, "short-year")}, ${clockOf(created)}</td>` +
          `<td data-label="From">${esc(s.source || "—")}</td><td data-label="Actions"><details class="confirm-details">` +
          `<summary class="btn btn--quiet btn--small">${icon("trash")}Remove<span class="visually-hidden"> ${esc(s.email)}</span></summary>` +
          `<div class="confirm-details__panel"><p>Remove ${esc(s.email)}?</p><button class="btn btn--danger btn--small" type="button" data-remove-subscriber="${s.id}">Yes, remove</button></div>` +
          `</details></td></tr>`;
      }).join("") + `</tbody></table>`;
    box.addEventListener("click", (event) => {
      const button = event.target.closest("[data-remove-subscriber]");
      if (!button) return;
      const id = Number(button.getAttribute("data-remove-subscriber"));
      const subscriber = db.subscribers.find((s) => s.id === id);
      db.subscribers = db.subscribers.filter((s) => s.id !== id);
      save();
      flash("success", `Removed ${subscriber ? subscriber.email : "the address"} from the list.`);
      reload();
    });
  }

  /* Start --------------------------------------------------------------------------------------------------- */

  const PAGES = {
    home: renderHome,
    menu: renderMenu,
    product: renderProduct,
    cart: initCart,
    checkout: initCheckout,
    order: renderOrder,
    reserve: initReserve,
    reservation: renderReservation,
    contact: initContact,
    "staff-dashboard": renderDashboard,
    "staff-products": renderStaffProducts,
    "staff-product-new": () => initProductForm(false),
    "staff-product-edit": () => initProductForm(true),
    "staff-product-delete": renderProductDelete,
    "staff-orders": renderStaffOrders,
    "staff-order": renderStaffOrder,
    "staff-reservations": renderStaffReservations,
    "staff-reservation": renderStaffReservation,
    "staff-messages": renderStaffMessages,
    "staff-message": renderStaffMessage,
    "staff-subscribers": renderSubscribers,
  };

  showPendingFlash();
  if (!storageOk) showStorageProblem();
  setCartBadge(cartCount(), false);
  initNewsletter();
  initReset();
  if (PAGE.indexOf("staff") === 0) renderStaffCounts();
  try {
    (PAGES[PAGE] || function () {})();
  } catch (error) {
    showFlash("error", "Something went wrong while showing this page. Resetting the demo (on the About page) usually fixes it.");
    if (window.console) window.console.error(error);
  }
})();
