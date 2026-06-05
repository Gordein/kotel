// Generate a per-form idempotency key so double-submits / retries don't duplicate.
document.addEventListener("htmx:configRequest", (e) => {
  const form = e.detail.elt.closest("form");
  if (form && form.dataset.idempotent && !form.dataset.reqid) {
    form.dataset.reqid = (crypto.randomUUID && crypto.randomUUID()) ||
      String(Date.now()) + Math.random().toString(16).slice(2);
  }
  if (form && form.dataset.reqid) e.detail.parameters["request_id"] = form.dataset.reqid;
});

// For plain (non-HTMX) form posts, inject a request_id hidden field on submit.
document.addEventListener("submit", (e) => {
  const form = e.target;
  if (form.dataset && form.dataset.idempotent && !form.querySelector('input[name=request_id]')) {
    const id = (crypto.randomUUID && crypto.randomUUID()) ||
      String(Date.now()) + Math.random().toString(16).slice(2);
    const i = document.createElement("input");
    i.type = "hidden"; i.name = "request_id"; i.value = id;
    form.appendChild(i);
  }
}, true);

// PWA service worker.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () =>
    navigator.serviceWorker.register("/static/sw.js").catch(() => {}));
}
