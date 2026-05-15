// Site-wide interactivity:
//   - theme toggle (light/dark) + named theme picker (71 themes from awesome-design-md)
//   - mobile chipbar disclosure
//   - scroll-spy TOC
//   - back-to-top button
//   - mermaid theme sync

(function () {
  "use strict";

  const root = document.documentElement;
  const STORAGE_KEY = "os-review-theme";

  /* ---- theme storage ---- */
  function read() {
    try {
      return localStorage.getItem(STORAGE_KEY) || "";
    } catch {
      return "";
    }
  }
  function write(v) {
    try {
      if (v) localStorage.setItem(STORAGE_KEY, v);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }

  // Apply persisted theme as early as possible (head inline already does this; this is defensive).
  const stored = read();
  if (stored) root.setAttribute("data-theme", stored);

  function currentTheme() {
    const explicit = root.getAttribute("data-theme");
    if (explicit) return explicit;
    return matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function isDarkTheme(slug) {
    if (!slug || slug === "auto") {
      return matchMedia("(prefers-color-scheme: dark)").matches;
    }
    if (slug === "dark") return true;
    if (slug === "light") return false;
    const t = (window.__THEMES__ || []).find((x) => x.slug === slug);
    if (t) return !!t.is_dark;
    return matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function setTheme(slug) {
    if (!slug) {
      root.removeAttribute("data-theme");
      write("");
    } else {
      root.setAttribute("data-theme", slug);
      write(slug);
    }
    syncMermaidTheme();
    refreshActiveCards();
  }

  /* ---- delegated click: toggle + named theme buttons ---- */
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-theme-toggle]");
    if (t) {
      const cur = currentTheme();
      setTheme(isDarkTheme(cur) ? "light" : "dark");
      return;
    }
    const s = e.target.closest("[data-theme-set]");
    if (s) {
      setTheme(s.getAttribute("data-theme-set") || "");
      return;
    }
  });

  /* ---- mobile chipbar disclosure ---- */
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-chipbar-toggle]");
    if (!btn) return;
    const track = document.querySelector(".chipbar-track");
    if (!track) return;
    const open = track.classList.toggle("open");
    btn.setAttribute("aria-expanded", String(open));
  });

  /* ---- theme picker drawer ---- */
  function setupPicker() {
    const panel = document.querySelector("[data-theme-panel]");
    const backdrop = document.querySelector("[data-theme-panel-backdrop]");
    const grid = document.querySelector("[data-theme-grid]");
    const openBtns = document.querySelectorAll("[data-theme-picker]");
    const closeBtns = document.querySelectorAll("[data-theme-panel-close]");
    if (!panel || !grid) return;

    function open() {
      renderGrid();
      panel.hidden = false;
      if (backdrop) backdrop.hidden = false;
      panel.setAttribute("aria-hidden", "false");
    }
    function close() {
      panel.hidden = true;
      if (backdrop) backdrop.hidden = true;
      panel.setAttribute("aria-hidden", "true");
    }
    openBtns.forEach((b) => b.addEventListener("click", open));
    closeBtns.forEach((b) => b.addEventListener("click", close));
    backdrop?.addEventListener("click", close);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !panel.hidden) close();
    });

    function renderGrid() {
      const themes = window.__THEMES__ || [];
      const cur = currentTheme();
      grid.innerHTML = themes.map((t) => themeCard(t, cur === t.slug)).join("");
    }
  }

  function themeCard(t, active) {
    const swatch = (t.swatch || [])
      .slice(0, 4)
      .map((c) => `<span style="background:${c}"></span>`)
      .join("");
    return `<button type="button" class="theme-card${active ? " theme-card-active" : ""}" data-theme-set="${t.slug}">
      <div class="theme-card-swatch">${swatch}</div>
      <div class="theme-card-name">${escHtml(t.name)} <span class="theme-card-mode">${t.is_dark ? "dark" : "light"}</span></div>
      <div class="theme-card-desc">${escHtml(t.description || "")}</div>
    </button>`;
  }

  function escHtml(s) {
    return String(s).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  }

  function refreshActiveCards() {
    const cur = currentTheme();
    document.querySelectorAll("[data-theme-set]").forEach((el) => {
      const slug = el.getAttribute("data-theme-set");
      el.classList.toggle("theme-card-active", slug === cur);
      el.classList.toggle("is-active", slug === cur);
    });
  }

  /* ---- scroll-spy TOC ---- */
  function setupScrollSpy() {
    const tocLinks = Array.from(
      document.querySelectorAll(".page-toc a[href^='#']"),
    );
    if (!tocLinks.length) return;
    const map = new Map();
    tocLinks.forEach((a) => {
      const id = decodeURIComponent(a.getAttribute("href").slice(1));
      const el = document.getElementById(id);
      if (el) map.set(el, a);
    });
    if (!map.size) return;

    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((en) => en.isIntersecting)
          .sort(
            (a, b) =>
              a.target.getBoundingClientRect().top -
              b.target.getBoundingClientRect().top,
          );
        if (!visible.length) return;
        const target = visible[0].target;
        tocLinks.forEach((a) => a.classList.remove("toc-active"));
        const link = map.get(target);
        if (link) {
          link.classList.add("toc-active");
          const scroller = link.closest(".page-toc");
          if (scroller) {
            const lr = link.getBoundingClientRect();
            const sr = scroller.getBoundingClientRect();
            if (lr.top < sr.top + 8 || lr.bottom > sr.bottom - 8) {
              link.scrollIntoView({ block: "nearest" });
            }
          }
        }
      },
      { rootMargin: "-90px 0px -75% 0px", threshold: [0, 1.0] },
    );

    map.forEach((_, el) => io.observe(el));
  }

  /* ---- back-to-top button ---- */
  function setupBackToTop() {
    const btn = document.querySelector(".back-to-top");
    if (!btn) return;
    const onScroll = () => {
      if (window.scrollY > 480) btn.classList.add("show");
      else btn.classList.remove("show");
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---- mermaid ---- */
  function mermaidThemeName() {
    return isDarkTheme(currentTheme()) ? "dark" : "default";
  }

  function syncMermaidTheme() {
    if (!window.mermaid) return;
    try {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: mermaidThemeName(),
        securityLevel: "loose",
        flowchart: { htmlLabels: true, curve: "basis" },
      });
      document.querySelectorAll("pre.mermaid").forEach((el) => {
        if (el.dataset.processed) {
          el.removeAttribute("data-processed");
          el.innerHTML = el.dataset.src || el.textContent;
        } else {
          el.dataset.src = el.textContent;
        }
      });
      window.mermaid.run({ querySelector: "pre.mermaid" }).catch(() => {});
    } catch {}
  }

  function bootMermaid() {
    if (!window.mermaid) {
      return setTimeout(bootMermaid, 80);
    }
    document.querySelectorAll("pre.mermaid").forEach((el) => {
      if (!el.dataset.src) el.dataset.src = el.textContent;
    });
    syncMermaidTheme();
  }

  /* ---- follow system when no explicit pref ---- */
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (!read()) syncMermaidTheme();
  });

  /* ---- init ---- */
  function init() {
    setupScrollSpy();
    setupBackToTop();
    setupPicker();
    bootMermaid();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
