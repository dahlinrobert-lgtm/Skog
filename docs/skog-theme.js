/* Shared theme controller for all Skog pages. */
(() => {
  "use strict";
  const KEY = "skog.theme";
  const root = document.documentElement;
  const button = document.querySelector(".skog-theme-toggle");
  const getTheme = () => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === "light" || saved === "dark") return saved;
    } catch (_) {}
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };
  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    const dark = theme === "dark";
    if (button) {
      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute("aria-label", dark ? "Byt till ljust läge" : "Byt till mörkt läge");
      button.innerHTML = dark
        ? '<span aria-hidden="true">☀️</span><span>Ljust läge</span>'
        : '<span aria-hidden="true">🌙</span><span>Mörkt läge</span>';
    }
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#101812" : "#173d2b");
  };
  applyTheme(getTheme());
  if (button) {
    button.addEventListener("click", () => {
      const next = root.dataset.theme === "dark" ? "light" : "dark";
      try { localStorage.setItem(KEY, next); } catch (_) {}
      applyTheme(next);
    });
  }
})();
