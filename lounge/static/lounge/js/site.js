/* ZenLeaf Tea Lounge: small progressive enhancements. Every feature here also works without
   JavaScript, through normal links and form submissions. */
(function () {
  "use strict";

  var doc = document.documentElement;
  doc.classList.add("js");
  var FETCH_HEADERS = { "X-Requested-With": "fetch", "Accept": "application/json" };
  // The online demo (GitHub Pages) has no server: demo.js handles its forms, so the handlers below
  // that post to the server are skipped there.
  var DEMO = doc.hasAttribute("data-demo");

  /* Toast messages ------------------------------------------------------------------------- */
  var toast = document.querySelector("[data-toast]");
  var toastTimer = null;
  function showToast(text, isError, showAction) {
    if (!toast) return;
    toast.querySelector("[data-toast-text]").textContent = text;
    var action = toast.querySelector("[data-toast-action]");
    if (action) action.hidden = !showAction;
    toast.classList.toggle("is-error", !!isError);
    toast.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () { toast.hidden = true; }, 6000);
  }

  /* Busy state for submit buttons ------------------------------------------------------------ */
  function setBusy(button, busy) {
    if (!button) return;
    if (busy) {
      if (!button.dataset.label) button.dataset.label = button.innerHTML;
      if (button.dataset.pendingText) button.textContent = button.dataset.pendingText;
      button.classList.add("is-loading");
      button.setAttribute("aria-busy", "true");
      // Disable after the browser has read the form, so the button's own name/value still submits.
      window.setTimeout(function () { button.disabled = true; }, 0);
    } else {
      if (button.dataset.label) button.innerHTML = button.dataset.label;
      button.classList.remove("is-loading");
      button.removeAttribute("aria-busy");
      button.disabled = false;
    }
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (DEMO || event.defaultPrevented || !(form instanceof HTMLFormElement)) return;
    if (form.dataset.submitting === "1") { event.preventDefault(); return; }
    if (form.hasAttribute("data-pending-form") || form.querySelector("[data-pending-text]")) {
      form.dataset.submitting = "1";
      setBusy(event.submitter || form.querySelector("[type=submit]"), true);
    }
  });

  // Pages restored from the back/forward cache keep their busy buttons; reset them.
  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) return;
    document.querySelectorAll("form[data-submitting]").forEach(function (form) {
      delete form.dataset.submitting;
      form.querySelectorAll(".is-loading").forEach(function (b) { setBusy(b, false); });
    });
  });

  /* Mobile navigation --------------------------------------------------------------------------- */
  var toggle = document.querySelector("[data-nav-toggle]");
  if (toggle) {
    var nav = toggle.closest(".site-nav");
    var list = document.getElementById(toggle.getAttribute("aria-controls"));
    toggle.hidden = false;
    var setOpen = function (open, returnFocus) {
      nav.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      if (!open && returnFocus) toggle.focus();
    };
    // Disclosure pattern: focus stays on the button; the links come next in the tab order.
    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true", false);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && nav.classList.contains("is-open")) setOpen(false, true);
    });
    document.addEventListener("click", function (event) {
      if (nav.classList.contains("is-open") && !nav.contains(event.target)) setOpen(false, false);
    });
    list.addEventListener("focusout", function (event) {
      if (nav.classList.contains("is-open") && event.relatedTarget && !nav.contains(event.relatedTarget)) setOpen(false, false);
    });
    window.matchMedia("(min-width: 760px)").addEventListener("change", function (mq) { if (mq.matches) setOpen(false, false); });
  }

  /* Cart count in the header ---------------------------------------------------------------------- */
  function updateCartCount(count) {
    var badge = document.querySelector("[data-cart-count]");
    var label = document.querySelector("[data-cart-label]");
    if (badge) {
      badge.textContent = count;
      badge.toggleAttribute("data-empty", count === 0);
      badge.classList.remove("is-bumped");
      void badge.offsetWidth;
      badge.classList.add("is-bumped");
    }
    if (label) label.textContent = count + (count === 1 ? " item" : " items");
  }

  /* Add to cart without leaving the page ----------------------------------------------------------- */
  document.querySelectorAll("[data-cart-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (DEMO || !window.fetch) return;
      event.preventDefault();
      if (form.dataset.submitting === "1") return;
      form.dataset.submitting = "1";
      var button = event.submitter || form.querySelector("[type=submit]");
      setBusy(button, true);
      fetch(form.action, { method: "POST", body: new FormData(form), headers: FETCH_HEADERS, credentials: "same-origin" })
        .then(function (response) {
          return response.json().catch(function () { return { ok: false, message: "" }; });
        })
        .then(function (data) {
          if (typeof data.count === "number") updateCartCount(data.count);
          showToast(data.message || "Something went wrong. Please try again.", !data.ok, !!data.ok);
        })
        .catch(function () {
          showToast("Couldn't reach the server. Check your connection and try again.", true, false);
        })
        .finally(function () {
          delete form.dataset.submitting;
          setBusy(button, false);
        });
    });
  });

  /* Newsletter sign-up without leaving the page ------------------------------------------------------ */
  document.querySelectorAll("[data-newsletter-form]").forEach(function (form) {
    var status = form.querySelector("[data-newsletter-status]");
    var input = form.querySelector("input[type=email]");
    form.addEventListener("submit", function (event) {
      if (DEMO || !window.fetch) return;
      event.preventDefault();
      if (form.dataset.submitting === "1") return;
      var button = event.submitter || form.querySelector("[type=submit]");
      if (!input.value.trim()) {
        status.textContent = "Enter your email address.";
        status.className = "newsletter-form__status is-error";
        input.setAttribute("aria-invalid", "true");
        input.focus();
        return;
      }
      form.dataset.submitting = "1";
      setBusy(button, true);
      status.textContent = "";
      fetch(form.action, { method: "POST", body: new FormData(form), headers: FETCH_HEADERS, credentials: "same-origin" })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          status.textContent = data.message;
          status.className = "newsletter-form__status " + (data.ok ? "is-success" : "is-error");
          if (data.ok) { input.value = ""; input.removeAttribute("aria-invalid"); }
          else { input.setAttribute("aria-invalid", "true"); input.focus(); }
        })
        .catch(function () {
          status.textContent = "Couldn't reach the server. Please try again.";
          status.className = "newsletter-form__status is-error";
        })
        .finally(function () {
          delete form.dataset.submitting;
          setBusy(button, false);
        });
    });
  });

  /* Filters that apply as soon as they change -------------------------------------------------------- */
  document.querySelectorAll("[data-auto-submit]").forEach(function (control) {
    control.addEventListener("change", function () {
      if (control.form) control.form.requestSubmit ? control.form.requestSubmit() : control.form.submit();
    });
  });

  /* Move keyboard focus to a form's error summary --------------------------------------------------------- */
  var summary = document.querySelector("[data-error-summary]");
  if (summary) summary.focus();

  /* Staff: switch availability and visibility in place ------------------------------------------------------ */
  document.querySelectorAll("[data-toggle-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (DEMO || !window.fetch) return;
      event.preventDefault();
      var button = form.querySelector(".switch");
      if (button.classList.contains("is-loading")) return;
      button.classList.add("is-loading");
      button.setAttribute("aria-busy", "true");
      fetch(form.action, { method: "POST", body: new FormData(form), headers: FETCH_HEADERS, credentials: "same-origin" })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (!data.ok) throw new Error(data.message);
          button.setAttribute("aria-checked", data.value ? "true" : "false");
          button.querySelector(".switch__label").textContent = data.value ? button.dataset.on : button.dataset.off;
          showToast(data.message, false, false);
        })
        .catch(function () { showToast("That change didn't save. Please try again.", true, false); })
        .finally(function () { button.classList.remove("is-loading"); button.removeAttribute("aria-busy"); });
    });
  });

  /* Staff: preview the chosen product picture (its photo, or its drawing when it has no photo) ------------ */
  var preview = document.querySelector("[data-illustration-preview]");
  var picker = document.getElementById("id_illustration");
  if (preview && picker) {
    var photoKeys = (preview.dataset.photos || "").split(" ");
    picker.addEventListener("change", function () {
      if (picker.value) {
        preview.src = photoKeys.indexOf(picker.value) !== -1
          ? preview.dataset.photoBase + picker.value + "-480.webp"
          : preview.dataset.base + picker.value + ".svg";
      }
      preview.hidden = !picker.value;
    });
  }

  // Shared with demo.js, which renders the online demo's pages in the browser.
  window.ZenLeafUI = { showToast: showToast, setBusy: setBusy, updateCartCount: updateCartCount };
})();
