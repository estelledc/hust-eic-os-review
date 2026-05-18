// Site-wide interactivity:
//   - theme toggle (light/dark) + named theme picker (71 themes from awesome-design-md)
//   - mobile site navigation disclosure
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

  /* ---- mobile site navigation disclosure ---- */
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-site-nav-toggle]");
    if (!btn) return;
    const nav = document.querySelector(".site-nav");
    if (!nav) return;
    const open = nav.classList.toggle("is-open");
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

  /* ---- practice workbench ---- */
  function setupPracticeWorkbench() {
    const mount = document.querySelector("[data-practice-workbench]");
    if (!mount) return;

    const source = window.__PRACTICE_LABS__ || {};
    const tracks = source.tracks || [
      {
        id: "quick",
        title: "快速体验",
        description: "先完成核心步骤，建立全局认识。",
      },
      {
        id: "full",
        title: "完整实践",
        description: "按 Lab1 到 Lab9 完成全部阶段。",
      },
      { id: "exam", title: "考前重点", description: "聚焦高频机制和易错点。" },
    ];
    // labs 起初只有索引元数据（id / title / focus / phaseIds）。
    // 完整内容（phases/steps/coach/...）通过 fetch('practice-labs/{labId}.json') 按需加载，加载后原地合并。
    const labs = normalizeLabs(source.labs || []);
    const key = "os-review-practice-workbench";
    const starterTrackId = tracks.some((track) => track.id === "starter")
      ? "starter"
      : tracks[0]?.id || "full";
    const labFetchPromises = new Map();

    if (!labs.length) {
      mount.innerHTML = '<p class="practice-empty">暂无可用实践任务。</p>';
      return;
    }

    function normalizeLabs(inputLabs) {
      // v2 数据模型已是唯一形态（lab → phases → steps）。直接透传。
      return inputLabs;
    }

    function isLabHydrated(lab) {
      return Array.isArray(lab && lab.phases) && lab.phases.length > 0;
    }

    function ensureLabHydrated(labId) {
      const lab = labs.find((x) => x.id === labId);
      if (!lab) return Promise.resolve(null);
      if (isLabHydrated(lab)) return Promise.resolve(lab);
      if (labFetchPromises.has(labId)) return labFetchPromises.get(labId);
      const promise = fetch(`practice-labs/${encodeURIComponent(labId)}.json`, {
        cache: "force-cache",
      })
        .then((r) => {
          if (!r.ok) throw new Error(`fetch ${labId} failed: ${r.status}`);
          return r.json();
        })
        .then((full) => {
          // 把完整字段合并回索引条目
          Object.assign(lab, full);
          return lab;
        })
        .catch((err) => {
          console.warn("practice lab fetch failed", labId, err);
          return lab;
        });
      labFetchPromises.set(labId, promise);
      return promise;
    }

    function defaultState() {
      return {
        version: 3,
        activeTrack: starterTrackId,
        activeLabId: labs[0].id,
        activePhaseId: "prepare",
        activeStepId: "",
        answers: {},
        passed: {},
        feedback: {},
        hintLevels: {},
        reflections: {},
        misconceptions: {},
        showPortfolio: false,
        trackMenuOpen: false,
        legacy: null,
      };
    }

    function migrateState(saved) {
      const next = defaultState();
      if (!saved || typeof saved !== "object") return next;
      next.activeLabId = saved.activeLabId || next.activeLabId;
      next.answers = saved.answers || {};
      next.passed = saved.passed || {};
      next.feedback = saved.feedback || {};
      next.showPortfolio =
        saved.version >= 3 && !!(saved.showPortfolio || saved.showReport);
      next.legacy = saved.version >= 2 ? saved.legacy || null : saved;
      if (saved.hintLevels) next.hintLevels = saved.hintLevels;
      else if (saved.hints) {
        Object.entries(saved.hints).forEach(([k, v]) => {
          next.hintLevels[k] = v ? 1 : 0;
        });
      }
      next.reflections = saved.reflections || {};
      next.misconceptions = saved.misconceptions || {};
      if (
        saved.version >= 3 &&
        saved.activeTrack &&
        tracks.some((track) => track.id === saved.activeTrack)
      ) {
        next.activeTrack = saved.activeTrack;
      }
      if (saved.version >= 3 && saved.activePhaseId)
        next.activePhaseId = saved.activePhaseId;
      if (saved.version >= 3 && saved.activeStepId)
        next.activeStepId = saved.activeStepId;
      return next;
    }

    function load() {
      try {
        return migrateState(JSON.parse(localStorage.getItem(key) || "{}"));
      } catch {
        return defaultState();
      }
    }

    function save(state) {
      try {
        localStorage.setItem(key, JSON.stringify(state));
      } catch {}
    }

    const state = load();

    function taskKey(labId, stepId) {
      return `${labId}:${stepId}`;
    }

    function normalize(v) {
      return String(v || "")
        .trim()
        .replace(/\s+/g, " ")
        .toLowerCase();
    }

    function currentTrack() {
      return (
        tracks.find((track) => track.id === state.activeTrack) || tracks[0]
      );
    }

    function activeLab() {
      return labs.find((lab) => lab.id === state.activeLabId) || labs[0];
    }

    function activePhase(lab) {
      return (
        lab.phases.find((phase) => phase.id === state.activePhaseId) ||
        lab.phases[0]
      );
    }

    function stepTrackVisible(step) {
      const stepTracks = step.tracks || ["full"];
      return (
        stepTracks.includes(state.activeTrack) || state.activeTrack === "full"
      );
    }

    function visibleStepsForPhase(phase) {
      return (phase.steps || []).filter(stepTrackVisible);
    }

    function allVisibleSteps(lab) {
      return lab.phases.flatMap((phase) => visibleStepsForPhase(phase));
    }

    function visibleStepEntries(lab) {
      return lab.phases.flatMap((phase) =>
        visibleStepsForPhase(phase).map((step) => ({ phase, step })),
      );
    }

    function allSteps(lab) {
      return lab.phases.flatMap((phase) => phase.steps || []);
    }

    function labProgress(lab) {
      const steps = allVisibleSteps(lab);
      const done = steps.filter(
        (step) => state.passed[taskKey(lab.id, step.id)],
      ).length;
      return { done, total: steps.length };
    }

    function totalProgress() {
      return labs.reduce(
        (acc, lab) => {
          const p = labProgress(lab);
          acc.done += p.done;
          acc.total += p.total;
          return acc;
        },
        { done: 0, total: 0 },
      );
    }

    function activeLabIndex() {
      const index = labs.findIndex((lab) => lab.id === activeLab().id);
      return index < 0 ? 0 : index;
    }

    function openLab(labId) {
      state.activeLabId = labId;
      state.activePhaseId = "prepare";
      state.activeStepId = "";
      state.trackMenuOpen = false;
      save(state);
      render();
    }

    function focusedStepEntry(lab, phase) {
      const entries = visibleStepEntries(lab);
      if (!entries.length) return null;
      const explicit = entries.find(
        (entry) => entry.step.id === state.activeStepId,
      );
      if (explicit) return explicit;
      const phaseEntry = visibleStepsForPhase(phase)
        .map((step) => ({ phase, step }))
        .find((entry) => !state.passed[taskKey(lab.id, entry.step.id)]);
      if (phaseEntry) return phaseEntry;
      return (
        entries.find(
          (entry) => !state.passed[taskKey(lab.id, entry.step.id)],
        ) || entries[0]
      );
    }

    function nextStepInLearningPath(lab, stepId) {
      const entries = visibleStepEntries(lab);
      if (!entries.length) return null;
      const index = entries.findIndex((entry) => entry.step.id === stepId);
      if (index === -1) return entries[0];
      return entries[index + 1] || null;
    }

    function answerFor(labId, step) {
      const saved = state.answers[taskKey(labId, step.id)];
      if (saved !== undefined) return saved;
      // trace 默认为空数组：用户从候选区点选到答案区
      if (step.interaction === "trace") return [];
      if (step.interaction === "fill") return {};
      return "";
    }

    function setAnswer(labId, step, value) {
      state.answers[taskKey(labId, step.id)] = value;
      if (step.interaction === "reflection")
        state.reflections[taskKey(labId, step.id)] = value;
      save(state);
    }

    function validateCheck(check, value) {
      if (check.kind === "choice") return value === check.answer;
      if (check.kind === "commands") {
        const got = String(value || "")
          .split(/\n+/)
          .map(normalize)
          .filter(Boolean);
        const expected = (check.commands || []).map(normalize);
        return (
          got.length === expected.length &&
          expected.every((cmd, i) => got[i] === cmd)
        );
      }
      if (check.kind === "fills") {
        const obj = value || {};
        return Object.entries(check.answers || {}).every(([id, answers]) => {
          const got = normalize(obj[id]);
          return answers.some((ans) => got.includes(normalize(ans)));
        });
      }
      if (check.kind === "keywords") {
        const text = String(value || "");
        if (text.trim().length < (check.minLength || 0)) return false;
        return (check.keywords || []).every((kw) =>
          normalize(text).includes(normalize(kw)),
        );
      }
      if (check.kind === "codeKeywords") {
        const code = String(value || "");
        return (check.keywords || []).every((kw) =>
          normalize(code).includes(normalize(kw)),
        );
      }
      if (check.kind === "orderedItems") {
        const got = Array.isArray(value) ? value.map(normalize) : [];
        const expected = (check.answer || []).map(normalize);
        return (
          got.length === expected.length &&
          expected.every((item, i) => got[i] === item)
        );
      }
      if (check.kind === "reflection") {
        return String(value || "").trim().length >= (check.minLength || 12);
      }
      return false;
    }

    function validate(step, value) {
      const checks = step.checks || [];
      if (!checks.length && step.validator)
        return validateCheck(step.validator, value);
      return (
        checks.length > 0 &&
        checks.every((check) => validateCheck(check, value))
      );
    }

    function detectMisconception(step, value) {
      for (const item of step.misconceptions || []) {
        const detect = item.detect || {};
        if (detect.kind === "selected" && value === detect.value) return item;
        if (
          detect.kind === "missingKeyword" &&
          !normalize(value).includes(normalize(detect.keyword))
        )
          return item;
        if (detect.kind === "missingCommand") {
          const lines = String(value || "")
            .split(/\n+/)
            .map(normalize);
          if (!lines.includes(normalize(detect.command))) return item;
        }
        if (detect.kind === "orderedBefore" && Array.isArray(value)) {
          const normalized = value.map(normalize);
          const itemIndex = normalized.indexOf(normalize(detect.item));
          const beforeIndex = normalized.indexOf(normalize(detect.before));
          if (itemIndex !== -1 && beforeIndex !== -1 && itemIndex < beforeIndex)
            return item;
        }
      }
      return null;
    }

    function renderPracticeHeader(lab, phase, total, labP) {
      const percent = total.total
        ? Math.round((total.done / total.total) * 100)
        : 0;
      const menuOpen = !!state.trackMenuOpen;
      return `<section class="practice-workspace-head" aria-label="实践工作台状态">
        <div class="practice-workspace-copy">
          <p class="practice-kicker">实践工作台</p>
          <h2>现在学：${escHtml(lab.title)}</h2>
          <p>先完成「${escHtml(phase.title)}」：${escHtml(phase.purpose || "完成当前阶段。")}</p>
        </div>
        <div class="practice-workspace-controls">
          <div class="practice-track-menu-wrap">
            <button type="button" class="practice-path-button" data-practice-open-track-menu aria-expanded="${menuOpen}">
              <span>学习路径</span>
              <strong>${escHtml(currentTrack().title)}</strong>
            </button>
            <div class="practice-track-menu${menuOpen ? " is-open" : ""}"${menuOpen ? "" : " hidden"}>
              ${tracks
                .map(
                  (
                    track,
                  ) => `<button type="button" class="practice-track-option${track.id === state.activeTrack ? " is-active" : ""}" data-practice-track="${escHtml(track.id)}">
                    <span>${escHtml(track.title)}</span>
                    <small>${escHtml(track.description)}</small>
                    ${track.id === "starter" ? "<em>新手推荐</em>" : ""}
                  </button>`,
                )
                .join("")}
            </div>
          </div>
          <button type="button" class="btn btn-primary" data-practice-report>学习档案</button>
        </div>
        <div class="practice-workspace-progress">
          <span>总进度 ${total.done}/${total.total}</span>
          <strong>${labP.done}/${labP.total} 步完成</strong>
          <div class="practice-progress-bar" aria-hidden="true"><span style="width:${percent}%"></span></div>
        </div>
      </section>`;
    }

    function renderBeginnerGuide(lab) {
      if (!lab.beginner) return "";
      return `<section class="practice-beginner-guide" aria-label="零基础导入">
        <div class="practice-beginner-main">
          <p class="practice-kicker">先别急着做题</p>
          <h3>${escHtml(lab.beginner.firstGoal || "先把题目翻成白话。")}</h3>
          <p>${escHtml(lab.beginner.story || lab.focus)}</p>
          <p class="practice-beginner-why">${escHtml(lab.beginner.why || "")}</p>
        </div>
        <div class="practice-beginner-side">
          <h4>可以这样想</h4>
          <p>${escHtml(lab.beginner.analogy || "先找对象、再看顺序、最后解释状态变化。")}</p>
          <h4>先认识 3 个词</h4>
          <dl class="practice-glossary">
            ${(lab.beginner.glossary || [])
              .map(
                (item) =>
                  `<div><dt>${escHtml(item.term)}</dt><dd>${escHtml(item.meaning)}</dd></div>`,
              )
              .join("")}
          </dl>
        </div>
      </section>`;
    }

    function renderLabJourney(currentLab) {
      const index = activeLabIndex();
      const prev = labs[index - 1];
      const next = labs[index + 1];
      const p = labProgress(currentLab);
      return `<nav class="practice-lab-journey" aria-label="Lab 学习旅程">
        <button type="button" class="practice-journey-nav" data-practice-prev-lab${prev ? "" : " disabled"}>
          <span>上一关</span>
          <strong>${prev ? escHtml(prev.title) : "已经到开头"}</strong>
        </button>
        <div class="practice-journey-current">
          <p class="practice-kicker">Lab ${index + 1} / ${labs.length}</p>
          <h3>${escHtml(currentLab.title)}</h3>
          <p>${escHtml(currentLab.focus)}</p>
          <span>${p.done}/${p.total} 步 · 预计 ${escHtml(currentLab.estimatedMinutes)} 分钟</span>
        </div>
        <button type="button" class="practice-journey-nav is-next" data-practice-next-lab${next ? "" : " disabled"}>
          <span>下一关</span>
          <strong>${next ? escHtml(next.title) : "已经到结尾"}</strong>
        </button>
        <details class="practice-lab-drawer">
          <summary>全部 Lab</summary>
          <div class="practice-lab-tabs">
            ${labs
              .map((lab) => {
                const labState = labProgress(lab);
                const count = allVisibleSteps(lab).length;
                return `<button type="button" class="practice-lab-tab${lab.id === currentLab.id ? " is-active" : ""}" data-practice-open-lab="${escHtml(lab.id)}">
                  <span>${escHtml(lab.title)}</span>
                  <small>${labState.done}/${labState.total} · ${count} 步</small>
                </button>`;
              })
              .join("")}
          </div>
        </details>
      </nav>`;
    }

    function renderPhaseProgress(lab) {
      return `<div class="practice-phase-progress" role="tablist" aria-label="当前 Lab 阶段进度">
        ${lab.phases
          .map((phase, i) => {
            const steps = visibleStepsForPhase(phase);
            const done = steps.filter(
              (step) => state.passed[taskKey(lab.id, step.id)],
            ).length;
            const complete = steps.length > 0 && done === steps.length;
            return `<button type="button" class="practice-phase-step${phase.id === activePhase(lab).id ? " is-active" : ""}${complete ? " is-complete" : ""}" data-practice-open-phase="${escHtml(phase.id)}">
              <span class="practice-phase-number">${i + 1}</span>
              <span class="practice-phase-copy">
                <strong>${escHtml(phase.title)}</strong>
                <small>${done}/${steps.length}</small>
              </span>
            </button>`;
          })
          .join("")}
      </div>`;
    }

    function renderChoice(lab, step) {
      const current = answerFor(lab.id, step);
      return `<div class="practice-options">
        ${(step.options || [])
          .map(
            (option) => `<label class="practice-option">
              <input type="radio" name="${escHtml(step.id)}" value="${escHtml(option.value)}" data-practice-input data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}"${current === option.value ? " checked" : ""}>
              <span>${escHtml(option.label)}</span>
            </label>`,
          )
          .join("")}
      </div>`;
    }

    function renderTextarea(lab, step, className, rows, placeholder) {
      return `<textarea class="${className}" rows="${rows}" data-practice-input data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}" placeholder="${escHtml(placeholder)}">${escHtml(answerFor(lab.id, step) || step.starter || "")}</textarea>`;
    }

    function renderCode(lab, step) {
      return `<textarea class="practice-code" rows="8" spellcheck="false" data-practice-input data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}">${escHtml(answerFor(lab.id, step) || step.starter || "")}</textarea>`;
    }

    function renderCommand(lab, step) {
      return `<div class="practice-terminal">
        <div class="practice-terminal-head">命令模拟器</div>
        <textarea class="practice-command" rows="5" spellcheck="false" data-practice-input data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}" placeholder="每行输入一条命令">${escHtml(answerFor(lab.id, step) || step.starter || "")}</textarea>
      </div>`;
    }

    function renderFill(lab, step) {
      const current = answerFor(lab.id, step) || {};
      return `<div class="practice-fill-list">
        ${(step.blanks || [])
          .map(
            (blank) => `<label class="practice-fill">
              <span>${escHtml(blank.label)}</span>
              <input type="text" value="${escHtml(current[blank.id] || "")}" placeholder="${escHtml(blank.placeholder || "")}" data-practice-input data-fill-id="${escHtml(blank.id)}" data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}">
            </label>`,
          )
          .join("")}
      </div>`;
    }

    function renderTrace(lab, step) {
      const order = answerFor(lab.id, step);
      const allItems = step.items || step.checks?.[0]?.answer || [];
      const placed = new Set(order);
      const candidates = allItems.filter((item) => !placed.has(item));
      return `<div class="practice-trace" data-practice-trace="${escHtml(step.id)}">
        <div class="practice-trace-region practice-trace-candidates">
          <p class="practice-kicker">候选项</p>
          ${
            candidates.length
              ? candidates
                  .map(
                    (
                      item,
                    ) => `<button type="button" class="practice-trace-candidate" data-practice-trace-pick data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}" data-item="${escHtml(item)}" aria-label="加入答案：${escHtml(item)}">
                      <span class="practice-trace-pick-mark" aria-hidden="true">+</span>
                      ${escHtml(item)}
                    </button>`,
                  )
                  .join("")
              : `<p class="practice-empty-inline">所有候选项已加入下方顺序</p>`
          }
        </div>
        <div class="practice-trace-region practice-trace-answer">
          <p class="practice-kicker">你的顺序</p>
          ${
            order.length
              ? order
                  .map(
                    (item, i) => `<div class="practice-trace-item">
                      <span class="practice-trace-index">${i + 1}</span>
                      <strong>${escHtml(item)}</strong>
                      <div class="practice-trace-controls">
                        <button type="button" class="btn btn-mini" data-practice-trace-move="up" data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}" data-index="${i}" aria-label="上移 ${escHtml(item)}" ${i === 0 ? "disabled" : ""}>↑</button>
                        <button type="button" class="btn btn-mini" data-practice-trace-move="down" data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}" data-index="${i}" aria-label="下移 ${escHtml(item)}" ${i === order.length - 1 ? "disabled" : ""}>↓</button>
                        <button type="button" class="btn btn-mini" data-practice-trace-remove data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}" data-index="${i}" aria-label="移回候选区：${escHtml(item)}">×</button>
                      </div>
                    </div>`,
                  )
                  .join("")
              : `<p class="practice-empty-inline">点击上方候选项加入这里，按因果顺序排列</p>`
          }
        </div>
      </div>`;
    }

    function renderControl(lab, step) {
      if (step.interaction === "choice" || step.interaction === "diagnose")
        return renderChoice(lab, step);
      if (step.interaction === "fill") return renderFill(lab, step);
      if (step.interaction === "code") return renderCode(lab, step);
      if (step.interaction === "command") return renderCommand(lab, step);
      if (step.interaction === "trace") return renderTrace(lab, step);
      if (step.interaction === "reflection")
        return renderTextarea(
          lab,
          step,
          "practice-textarea",
          5,
          "写入你的复盘，学习档案会保存这段内容",
        );
      return renderTextarea(
        lab,
        step,
        "practice-textarea",
        4,
        "用自己的话写出解释",
      );
    }

    function renderHints(lab, step) {
      const visible = state.hintLevels[taskKey(lab.id, step.id)] || 0;
      if (!visible) return "";
      return `<div class="practice-hints">
        ${(step.hints || [])
          .slice(0, visible)
          .map(
            (hint) =>
              `<p class="practice-hint"><strong>提示 ${hint.level}</strong>${escHtml(hint.text)}</p>`,
          )
          .join("")}
      </div>`;
    }

    function renderRepairFeedback(lab, step) {
      const keyForStep = taskKey(lab.id, step.id);
      const feedback = state.feedback[keyForStep];
      if (!feedback) return "";
      if (feedback.ok) {
        return `<section class="practice-coach-result is-ok" aria-label="通过后的理解确认">
          <p class="practice-kicker">检查通过</p>
          <h4>你现在应该能说明</h4>
          <p>${escHtml(step.coach.check)}</p>
        </section>`;
      }
      const misconceptionId = state.misconceptions[keyForStep];
      const misconception = (step.misconceptions || []).find(
        (item) => item.id === misconceptionId,
      );
      return `<section class="practice-coach-result is-repair" aria-label="错因修正">
        <p class="practice-kicker">先修正一个混淆点</p>
        <h4>${misconception ? "你可能混淆了这里" : "这一步还没对上机制"}</h4>
        <p>${escHtml(feedback.message)}</p>
        <div class="practice-repair-drill">
          <strong>补救练习</strong>
          <span>${escHtml(step.coach.repair)}</span>
        </div>
      </section>`;
    }

    function renderCoachStep(lab, phase, step, index) {
      const keyForStep = taskKey(lab.id, step.id);
      const isPassed = !!state.passed[keyForStep];
      const hintLevel = state.hintLevels[keyForStep] || 0;
      const hintTotal = (step.hints || []).length || 1;
      const nextEntry = nextStepInLearningPath(lab, step.id);
      return `<article class="practice-coach-card${isPassed ? " is-complete" : ""}" data-practice-task="${escHtml(step.id)}">
        <header class="practice-coach-head">
          <div>
            <p class="practice-kicker">${escHtml(phase.title)} · 第 ${index + 1} 步</p>
            <h3>${escHtml(step.title)}</h3>
            <p>${escHtml(step.goal)}</p>
          </div>
          <span class="practice-task-type">${escHtml(step.interaction)}</span>
        </header>
        <section class="practice-coach-why">
          <h4>为什么先学这个</h4>
          <p>${escHtml(step.coach.why)}</p>
        </section>
        <section class="practice-coach-observe">
          <h4>先观察</h4>
          <p>${escHtml(step.coach.observe)}</p>
          ${renderSimulator(step)}
        </section>
        <section class="practice-coach-action">
          <h4>现在只做这一步</h4>
          <p class="practice-prompt">${escHtml(step.coach.act)}</p>
          ${renderControl(lab, step)}
        </section>
        <div class="practice-task-actions">
          <button type="button" class="btn btn-mini btn-primary" data-practice-check-task data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}">检查我的理解</button>
          <button type="button" class="btn btn-mini" data-practice-toggle-hint data-lab-id="${escHtml(lab.id)}" data-step-id="${escHtml(step.id)}">提示 ${Math.min(hintLevel + 1, hintTotal)}/${hintTotal}</button>
          ${
            nextEntry
              ? `<button type="button" class="btn btn-mini" data-practice-next-step data-step-id="${escHtml(nextEntry.step.id)}" data-phase-id="${escHtml(nextEntry.phase.id)}">继续下一步</button>`
              : `<span class="practice-empty-inline">本 Lab 的当前路径已到最后一步</span>`
          }
        </div>
        ${renderHints(lab, step)}
        ${renderRepairFeedback(lab, step)}
      </article>`;
    }

    function renderLearningRoute(lab, activeStep) {
      const entries = visibleStepEntries(lab);
      return `<aside class="practice-learning-route" aria-label="本 Lab 学习路线">
        <div class="practice-route-head">
          <p class="practice-kicker">学习路线</p>
          <strong>一次只做当前高亮步骤</strong>
        </div>
        <div class="practice-route-list">
          ${entries
            .map((entry, i) => {
              const passed = !!state.passed[taskKey(lab.id, entry.step.id)];
              const active = activeStep && activeStep.id === entry.step.id;
              return `<button type="button" class="practice-route-step${active ? " is-active" : ""}${passed ? " is-complete" : ""}" data-practice-route-step data-step-id="${escHtml(entry.step.id)}" data-phase-id="${escHtml(entry.phase.id)}">
                <span>${i + 1}</span>
                <strong>${escHtml(entry.step.title)}</strong>
                <small>${escHtml(entry.phase.title)} · ${passed ? "已通过" : "待完成"}</small>
              </button>`;
            })
            .join("")}
        </div>
      </aside>`;
    }

    function renderSimulator(step) {
      if (!step) return "";
      const sim = step.simulator || {};
      const kind = sim.kind;
      if (!kind) return "";
      const nodes = sim.nodes || [];
      const highlight = new Set(sim.highlightOnPass || []);

      if (kind === "terminal") {
        return `<pre class="practice-sim practice-sim-terminal" data-sim-kind="terminal">${escHtml(sim.output || "# simulated output")}</pre>`;
      }
      if (kind === "concept-map") {
        return `<div class="practice-sim practice-sim-concept-map" data-sim-kind="concept-map" aria-label="概念对象映射">
          ${nodes
            .map(
              (n) =>
                `<div class="practice-sim-concept-node"><strong>${escHtml(n)}</strong></div>`,
            )
            .join("")}
        </div>`;
      }
      if (kind === "state-flow") {
        return `<ol class="practice-sim practice-sim-state-flow" data-sim-kind="state-flow" aria-label="状态流">
          ${nodes
            .map(
              (n) =>
                `<li class="practice-sim-flow-node${highlight.has(n) ? " is-highlight" : ""}"><span class="practice-sim-flow-arrow" aria-hidden="true">→</span><span>${escHtml(n)}</span></li>`,
            )
            .join("")}
        </ol>`;
      }
      if (kind === "state-note") {
        return `<dl class="practice-sim practice-sim-state-note" data-sim-kind="state-note" aria-label="状态备忘">
          ${nodes
            .map(
              (n) =>
                `<div class="practice-sim-state-item"><dt>${escHtml(n)}</dt><dd>关注它在本步是否变化</dd></div>`,
            )
            .join("")}
        </dl>`;
      }
      if (kind === "code-context") {
        return `<pre class="practice-sim practice-sim-code-context" data-sim-kind="code-context" aria-label="关键词上下文"><code>${nodes.map((n) => `<span class="practice-sim-code-token">${escHtml(n)}</span>`).join("\n")}</code></pre>`;
      }
      if (kind === "failure-card") {
        return `<aside class="practice-sim practice-sim-failure-card" data-sim-kind="failure-card" aria-label="故障线索">
          <h5>故障线索</h5>
          <ul>${nodes.map((n) => `<li>${escHtml(n)}</li>`).join("")}</ul>
        </aside>`;
      }
      // 未知 kind：不渲染（暴露数据问题，不静默 fallback）
      return "";
    }

    function renderFirstPrinciples(lab) {
      const firstPrinciples = lab.firstPrinciples || {};
      const groups = [
        ["actors", "谁在行动"],
        ["state", "状态在哪里"],
        ["boundary", "关键边界"],
        ["transition", "动作改变什么"],
        ["evidence", "证据怎么观察"],
        ["failureModes", "错了先查哪里"],
      ].filter(
        ([keyForGroup]) =>
          Array.isArray(firstPrinciples[keyForGroup]) &&
          firstPrinciples[keyForGroup].length,
      );
      if (!groups.length) return "";
      return `<section class="practice-side-card practice-first-principles">
        <p class="practice-kicker">第一性原理</p>
        <h3>先看懂机制骨架</h3>
        <div class="practice-principles-grid">
          ${groups
            .map(
              ([keyForGroup, label]) => `<div class="practice-principle">
                <strong>${escHtml(label)}</strong>
                <ul>${firstPrinciples[keyForGroup]
                  .slice(0, 3)
                  .map((item) => `<li>${escHtml(item)}</li>`)
                  .join("")}</ul>
              </div>`,
            )
            .join("")}
        </div>
      </section>`;
    }

    function renderMechanismBoard(lab, phase, step) {
      const model = lab.mentalModel || {};
      const misconceptionCount = Object.entries(state.misconceptions).filter(
        ([keyForStep]) => keyForStep.startsWith(`${lab.id}:`),
      ).length;
      const observeText = step
        ? step.coach.observe
        : phase.purpose || lab.focus;
      return `<aside class="practice-side practice-mechanism-board" aria-label="机制画板">
        <section class="practice-side-card practice-mechanism-card">
          <p class="practice-kicker">这一关要回答</p>
          <h3>${escHtml(lab.drivingQuestion || lab.focus)}</h3>
          <p>${escHtml(model.explanation || lab.focus)}</p>
          <div class="practice-model-flow">
            ${(model.flow || lab.concepts || []).map((item) => `<span>${escHtml(item)}</span>`).join("")}
          </div>
        </section>
        <section class="practice-side-card">
          <h3>当前步骤观察点</h3>
          <p>${escHtml(observeText)}</p>
          ${(model.checkpoints || []).length ? `<ul>${model.checkpoints.map((x) => `<li>${escHtml(x)}</li>`).join("")}</ul>` : ""}
        </section>
        ${renderFirstPrinciples(lab)}
        <details class="practice-side-card practice-side-details">
          <summary>更多参考</summary>
          ${
            lab.beginner
              ? `<div class="practice-side-detail-block">
                  <h4>看不懂先看这 3 个词</h4>
                  <dl class="practice-glossary compact">
                    ${(lab.beginner.glossary || [])
                      .map(
                        (item) =>
                          `<div><dt>${escHtml(item.term)}</dt><dd>${escHtml(item.meaning)}</dd></div>`,
                      )
                      .join("")}
                  </dl>
                </div>`
              : ""
          }
          <div class="practice-side-detail-block">
            <h4>迁移到真实实验</h4>
            <ul>${(lab.transferChecklist || []).map((x) => `<li>${escHtml(x)}</li>`).join("")}</ul>
          </div>
          <div class="practice-side-detail-block">
            <p>已记录 ${misconceptionCount} 个错因。使用过三层提示的步骤会进入待复习列表。</p>
            <button type="button" class="btn" data-practice-reset>清空当前 Lab 进度</button>
          </div>
        </details>
      </aside>`;
    }

    function renderLearningPortfolio() {
      if (!state.showPortfolio) return "";
      const lines = [
        "# Lab Studio 学习档案",
        "",
        `当前路径：${currentTrack().title}`,
        "",
      ];
      labs.forEach((lab) => {
        const p = labProgress(lab);
        lines.push(`## ${lab.title}`);
        lines.push(`完成度：${p.done}/${p.total}`);
        const labReflections = Object.entries(state.reflections).filter(
          ([keyForStep]) => keyForStep.startsWith(`${lab.id}:`),
        );
        if (labReflections.length) {
          lines.push("", "### 我的复盘");
          labReflections.forEach(([, value]) =>
            lines.push(`- ${String(value).replace(/\n+/g, " ")}`),
          );
        }
        const labMisconceptions = Object.entries(state.misconceptions).filter(
          ([keyForStep]) => keyForStep.startsWith(`${lab.id}:`),
        );
        if (labMisconceptions.length) {
          lines.push("", "### 错因记录");
          labMisconceptions.forEach(([, value]) => lines.push(`- ${value}`));
        }
        const deepHints = allSteps(lab).filter(
          (step) => (state.hintLevels[taskKey(lab.id, step.id)] || 0) >= 3,
        );
        if (deepHints.length) {
          lines.push("", "### 待复习步骤");
          deepHints.forEach((step) => lines.push(`- ${step.title}`));
        }
        lines.push("", "### 报告段落提示");
        (lab.reportPrompts || []).forEach((prompt) =>
          lines.push(`- ${prompt}`),
        );
        lines.push("");
      });
      return `<aside class="practice-report-panel" data-practice-report-panel>
        <div class="practice-report-head">
          <h3>学习档案</h3>
          <button type="button" class="theme-picker-close" aria-label="关闭学习档案" data-practice-close-report>×</button>
        </div>
        <textarea class="practice-report-text" rows="18" readonly>${escHtml(lines.join("\n"))}</textarea>
      </aside>`;
    }

    function render() {
      const lab = activeLab();
      if (!lab.phases.some((phase) => phase.id === state.activePhaseId))
        state.activePhaseId = lab.phases[0].id;
      const phase = activePhase(lab);
      const focused = focusedStepEntry(lab, phase);
      const activeEntry = focused || { phase, step: null };
      state.activePhaseId = activeEntry.phase.id;
      const activePhaseNow = activeEntry.phase;
      const step = activeEntry.step;
      const routeEntries = visibleStepEntries(lab);
      const stepIndex = Math.max(
        0,
        routeEntries.findIndex((entry) => step && entry.step.id === step.id),
      );
      const total = totalProgress();
      const labP = labProgress(lab);
      mount.innerHTML = `<div class="practice-studio">
        ${renderPracticeHeader(lab, activePhaseNow, total, labP)}
        ${renderLabJourney(lab)}
        <div class="practice-shell">
          <main class="practice-stage">
            <header class="practice-stage-head">
              <p class="practice-kicker">${escHtml(lab.id.toUpperCase())} · ${escHtml(currentTrack().title)}</p>
              <h2>${escHtml(lab.title)}</h2>
              <p>${escHtml(lab.focus)}</p>
              <div class="practice-stage-meta">
                <span>${labP.done}/${labP.total} 步完成</span>
                <span>预计 ${escHtml(lab.estimatedMinutes)} 分钟</span>
                <span>${escHtml((lab.sourceRoute && lab.sourceRoute.name) || "HIT-OSlab route")}</span>
              </div>
            </header>
            ${renderBeginnerGuide(lab)}
            ${renderPhaseProgress(lab)}
            <div class="practice-coach-layout">
              ${
                step
                  ? renderCoachStep(lab, activePhaseNow, step, stepIndex)
                  : `<section class="practice-coach-card"><p class="practice-empty">当前路径在这一阶段没有步骤，请切换到其他阶段或路径。</p></section>`
              }
              ${renderLearningRoute(lab, step)}
            </div>
          </main>
          ${renderMechanismBoard(lab, activePhaseNow, step)}
        </div>
      </div>${renderLearningPortfolio()}`;
    }

    function findStep(labId, stepId) {
      const lab = labs.find((x) => x.id === labId);
      const step = lab ? allSteps(lab).find((x) => x.id === stepId) : null;
      return { lab, step };
    }

    function currentValueForInput(input) {
      const labId = input.getAttribute("data-lab-id");
      const stepId = input.getAttribute("data-step-id");
      const { step } = findStep(labId, stepId);
      if (!step) return;
      state.activeStepId = stepId;
      if (step.interaction === "choice" || step.interaction === "diagnose") {
        if (input.checked) setAnswer(labId, step, input.value);
        return;
      }
      if (step.interaction === "fill") {
        const current = answerFor(labId, step) || {};
        current[input.getAttribute("data-fill-id")] = input.value;
        setAnswer(labId, step, current);
        return;
      }
      setAnswer(labId, step, input.value);
    }

    function clearCurrentLab() {
      const lab = activeLab();
      allSteps(lab).forEach((step) => {
        const keyForStep = taskKey(lab.id, step.id);
        delete state.answers[keyForStep];
        delete state.passed[keyForStep];
        delete state.feedback[keyForStep];
        delete state.hintLevels[keyForStep];
        delete state.reflections[keyForStep];
        delete state.misconceptions[keyForStep];
      });
      state.showPortfolio = false;
      save(state);
      render();
    }

    mount.addEventListener("input", (e) => {
      const input = e.target.closest("[data-practice-input]");
      if (input) currentValueForInput(input);
    });

    mount.addEventListener("change", (e) => {
      const input = e.target.closest("[data-practice-input]");
      if (input) currentValueForInput(input);
    });

    mount.addEventListener("click", (e) => {
      const trackMenuButton = e.target.closest(
        "[data-practice-open-track-menu]",
      );
      if (trackMenuButton) {
        state.trackMenuOpen = !state.trackMenuOpen;
        render();
        return;
      }

      const trackButton = e.target.closest("[data-practice-track]");
      if (trackButton) {
        state.activeTrack = trackButton.getAttribute("data-practice-track");
        state.activeStepId = "";
        state.trackMenuOpen = false;
        save(state);
        render();
        return;
      }

      const prevLabButton = e.target.closest("[data-practice-prev-lab]");
      if (prevLabButton && !prevLabButton.disabled) {
        const previousLab = labs[activeLabIndex() - 1];
        if (previousLab) openLab(previousLab.id);
        return;
      }

      const nextLabButton = e.target.closest("[data-practice-next-lab]");
      if (nextLabButton && !nextLabButton.disabled) {
        const nextLab = labs[activeLabIndex() + 1];
        if (nextLab) openLab(nextLab.id);
        return;
      }

      const labButton = e.target.closest("[data-practice-open-lab]");
      if (labButton) {
        openLab(labButton.getAttribute("data-practice-open-lab"));
        return;
      }

      const phaseButton = e.target.closest("[data-practice-open-phase]");
      if (phaseButton) {
        state.activePhaseId = phaseButton.getAttribute(
          "data-practice-open-phase",
        );
        state.activeStepId = "";
        save(state);
        render();
        return;
      }

      const routeStepButton = e.target.closest("[data-practice-route-step]");
      if (routeStepButton) {
        state.activePhaseId =
          routeStepButton.getAttribute("data-phase-id") || state.activePhaseId;
        state.activeStepId = routeStepButton.getAttribute("data-step-id") || "";
        save(state);
        render();
        return;
      }

      const nextStepButton = e.target.closest("[data-practice-next-step]");
      if (nextStepButton) {
        state.activePhaseId =
          nextStepButton.getAttribute("data-phase-id") || state.activePhaseId;
        state.activeStepId = nextStepButton.getAttribute("data-step-id") || "";
        save(state);
        render();
        setTimeout(() => {
          document
            .querySelector(`[data-practice-task="${state.activeStepId}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 0);
        return;
      }

      const traceMove = e.target.closest("[data-practice-trace-move]");
      if (traceMove) {
        const labId = traceMove.getAttribute("data-lab-id");
        const stepId = traceMove.getAttribute("data-step-id");
        const { step } = findStep(labId, stepId);
        if (!step) return;
        const order = answerFor(labId, step).slice();
        const index = Number(traceMove.getAttribute("data-index"));
        const dir = traceMove.getAttribute("data-practice-trace-move");
        const nextIndex = dir === "up" ? index - 1 : index + 1;
        if (nextIndex >= 0 && nextIndex < order.length) {
          [order[index], order[nextIndex]] = [order[nextIndex], order[index]];
          state.activeStepId = stepId;
          setAnswer(labId, step, order);
          render();
        }
        return;
      }

      const tracePick = e.target.closest("[data-practice-trace-pick]");
      if (tracePick) {
        const labId = tracePick.getAttribute("data-lab-id");
        const stepId = tracePick.getAttribute("data-step-id");
        const item = tracePick.getAttribute("data-item");
        const { step } = findStep(labId, stepId);
        if (!step || !item) return;
        const order = answerFor(labId, step).slice();
        if (!order.includes(item)) order.push(item);
        state.activeStepId = stepId;
        setAnswer(labId, step, order);
        render();
        return;
      }

      const traceRemove = e.target.closest("[data-practice-trace-remove]");
      if (traceRemove) {
        const labId = traceRemove.getAttribute("data-lab-id");
        const stepId = traceRemove.getAttribute("data-step-id");
        const { step } = findStep(labId, stepId);
        if (!step) return;
        const order = answerFor(labId, step).slice();
        const index = Number(traceRemove.getAttribute("data-index"));
        if (index >= 0 && index < order.length) {
          order.splice(index, 1);
          state.activeStepId = stepId;
          setAnswer(labId, step, order);
          render();
        }
        return;
      }

      const hintButton = e.target.closest("[data-practice-toggle-hint]");
      if (hintButton) {
        const labId = hintButton.getAttribute("data-lab-id");
        const stepId = hintButton.getAttribute("data-step-id");
        const { step } = findStep(labId, stepId);
        if (!step) return;
        const keyForStep = taskKey(labId, stepId);
        state.activeStepId = stepId;
        state.hintLevels[keyForStep] = Math.min(
          (state.hintLevels[keyForStep] || 0) + 1,
          (step.hints || []).length || 1,
        );
        save(state);
        render();
        return;
      }

      const checkButton = e.target.closest("[data-practice-check-task]");
      if (checkButton) {
        const labId = checkButton.getAttribute("data-lab-id");
        const stepId = checkButton.getAttribute("data-step-id");
        const { step } = findStep(labId, stepId);
        if (!step) return;
        const keyForStep = taskKey(labId, stepId);
        const value = answerFor(labId, step);
        const ok = validate(step, value);
        const misconception = ok ? null : detectMisconception(step, value);
        state.activeStepId = stepId;
        state.passed[keyForStep] = ok;
        if (misconception) state.misconceptions[keyForStep] = misconception.id;
        state.feedback[keyForStep] = {
          ok,
          message: ok
            ? step.success
            : misconception?.feedback ||
              step.feedback ||
              "还没有通过，请根据提示重新检查。",
        };
        if (ok && step.interaction === "reflection")
          state.reflections[keyForStep] = value;
        save(state);
        render();
        return;
      }

      if (e.target.closest("[data-practice-report]")) {
        state.showPortfolio = true;
        save(state);
        render();
        return;
      }

      if (e.target.closest("[data-practice-close-report]")) {
        state.showPortfolio = false;
        save(state);
        render();
        return;
      }

      if (e.target.closest("[data-practice-reset]")) {
        clearCurrentLab();
      }
    });

    // 索引立即可用：渲染骨架；并行 hydrate 所有 lab，全部就绪再切到完整 render。
    function renderLoadingShell() {
      mount.innerHTML = `<div class="practice-studio">
        <p class="practice-loading">正在加载实践数据...</p>
      </div>`;
    }

    function bootstrap() {
      const allHydrated = labs.every(isLabHydrated);
      if (allHydrated) {
        render();
        return;
      }
      renderLoadingShell();
      Promise.all(labs.map((lab) => ensureLabHydrated(lab.id))).then(() => {
        render();
      });
    }

    bootstrap();
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
    setupPracticeWorkbench();
    setupPicker();
    bootMermaid();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
