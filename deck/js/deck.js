// Slide engine: one 1920 x 1080 stage scaled to the window, slides with steps, speaker notes.
// Keys: Right / Space / PageDown next, Left / PageUp back, N notes, F fullscreen, R restart slide,
// M live or scripted (on a demo slide, in live mode).
(function () {
  const stage = document.getElementById("stage");
  const slides = Array.from(document.querySelectorAll(".slide"));
  const notesEl = document.getElementById("notes");
  const pager = document.getElementById("pager");
  const handlers = {};
  let idx = 0;
  let step = 0;

  const Deck = (window.Deck = {
    // register(id, { steps, enter(), step(n), leave(), busy(), hurry() })
    register(id, h) { handlers[id] = h; },
    next, prev, go: show,
    busy() { const h = handlers[slides[idx].id]; return !!(h && h.busy && h.busy()); },
    get index() { return idx; },
    get step() { return step; }
  });

  // Live or scripted, per demo. In live mode a demo slide carries a small switch (and the key M):
  // if the live version sticks, the scripted one is one click away. Kept for this browser tab.
  let mocks = {};
  try { mocks = JSON.parse(sessionStorage.getItem("olli-mock") || "{}"); } catch (e) { mocks = {}; }
  const toggles = {};
  Deck.mock = (key) => !!mocks[key];
  // before(): the mode that is on screen cleans up. after(): the other one takes over.
  Deck.liveSwitch = function (slide, key, before, after) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "livesw";
    b.title = "key M";
    const paint = () => {
      b.innerHTML = mocks[key] ? "scripted · <u>back to live</u>" : "<i>●</i> live · <u>switch to scripted</u>";
      b.classList.toggle("mock", !!mocks[key]);
    };
    const flip = () => {
      if (before) before();
      mocks[key] = !mocks[key];
      try { sessionStorage.setItem("olli-mock", JSON.stringify(mocks)); } catch (e) { /* private window */ }
      paint();
      b.blur();
      if (after) after(!!mocks[key]);
    };
    b.addEventListener("click", flip);
    toggles[slide.id] = flip;
    slide.appendChild(b);
    paint();
    return { paint: paint };
  };

  function fit() {
    const s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.transform = "translate(-50%, -50%) scale(" + s + ")";
  }

  function maxSteps(i) {
    const h = handlers[slides[i].id];
    if (h && typeof h.steps === "number") return h.steps;
    const frags = slides[i].querySelectorAll("[data-step]");
    let m = +(slides[i].dataset.steps || 0);
    frags.forEach((f) => { m = Math.max(m, +f.dataset.step); });
    return m;
  }

  function applyFragments() {
    slides[idx].querySelectorAll("[data-step]").forEach((f) => {
      f.classList.toggle("on", +f.dataset.step <= step);
    });
  }

  function updateChrome() {
    const s = slides[idx];
    const n = s.querySelector(".notes");
    notesEl.innerHTML = '<div class="t">' + (idx + 1) + " / " + slides.length + " · " + s.id +
      " · step " + step + " of " + maxSteps(idx) + "</div>" + (n ? n.innerHTML : "");
    pager.textContent = (idx + 1) + "/" + slides.length;
    if (history.replaceState) history.replaceState(null, "", "#" + (idx + 1));
  }

  function show(i) {
    i = Math.max(0, Math.min(slides.length - 1, i));
    const old = handlers[slides[idx].id];
    if (old && old.leave) old.leave();
    idx = i;
    step = 0;
    slides.forEach((s, k) => s.classList.toggle("active", k === idx));
    applyFragments();
    const h = handlers[slides[idx].id];
    if (h && h.enter) h.enter();
    updateChrome();
  }

  function next() {
    const h = handlers[slides[idx].id];
    if (h && h.busy && h.busy()) { if (h.hurry) h.hurry(); return; }
    if (step < maxSteps(idx)) {
      step++;
      applyFragments();
      if (h && h.step) h.step(step);
      updateChrome();
    } else if (idx < slides.length - 1) {
      show(idx + 1);
    }
  }

  function prev() {
    const h = handlers[slides[idx].id];
    if (step > 0 && !(h && h.step)) {
      step--;
      applyFragments();
      updateChrome();
    } else if (step > 0) {
      show(idx); // scripted slides restart
    } else if (idx > 0) {
      show(idx - 1);
    }
  }

  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|TEXTAREA/.test((e.target && e.target.tagName) || "");
    const k = e.key;
    if (k === "PageDown") { e.preventDefault(); next(); return; }
    if (k === "PageUp") { e.preventDefault(); prev(); return; }
    if (typing) return;
    if (k === "ArrowRight" || k === " ") { e.preventDefault(); next(); }
    else if (k === "ArrowLeft") { e.preventDefault(); prev(); }
    else if (k === "Home") show(0);
    else if (k === "End") show(slides.length - 1);
    else if (k === "n" || k === "N") notesEl.classList.toggle("on");
    else if (k === "r" || k === "R") show(idx);
    else if (k === "m" || k === "M") { if (toggles[slides[idx].id]) toggles[slides[idx].id](); }
    else if (k === "f" || k === "F") {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen();
    }
  });

  // Live demos sit in iframes. After a click in there, the iframe sends navigation keys back here,
  // so the presenter remote keeps working. Only from the shop's own origin.
  window.addEventListener("message", (e) => {
    const m = e.data, cfg = window.OLLI_CONFIG || {};
    if (!m || m.type !== "olli:key" || !cfg.shopOrigin || e.origin !== cfg.shopOrigin) return;
    if (m.key === "PageDown" || m.key === "ArrowRight" || m.key === " ") next();
    else if (m.key === "PageUp" || m.key === "ArrowLeft") prev();
  });

  window.addEventListener("hashchange", () => {
    const n = parseInt((location.hash || "").replace("#", ""), 10);
    if (!isNaN(n) && n - 1 !== idx) show(n - 1);
  });
  window.addEventListener("resize", fit);
  window.addEventListener("DOMContentLoaded", () => {
    fit();
    if (window.OLLI_CONFIG && window.OLLI_CONFIG.showSimBadge === false) document.body.classList.add("hide-sim");
    // Logo slots: <span class="lg" data-logo="name">Name</span> gets its file from config.logos.
    const logos = (window.OLLI_CONFIG && window.OLLI_CONFIG.logos) || {};
    document.querySelectorAll(".lg").forEach((e) => {
      const entry = logos[e.dataset.logo];
      const src = entry && (entry.src || entry);
      const slot = document.createElement(src ? "img" : "span");
      slot.className = "lgslot" + (src ? "" : " empty");
      if (src) { slot.src = src; slot.alt = ""; }
      if (src && entry.wordmark) { slot.alt = e.textContent; e.textContent = ""; e.classList.add("wm"); }
      e.prepend(slot);
    });
    // Links into the OpenShift console: <span data-console="/path">label</span> becomes a link when the
    // live config knows the console (consoleBase, from "make deck-live"). The console refuses to be
    // framed, so it opens in a tab of its own. Without a console the label stays, or hides.
    const base = (window.OLLI_CONFIG && window.OLLI_CONFIG.consoleBase) || "";
    document.querySelectorAll("[data-console]").forEach((e) => {
      if (!base) { if (e.dataset.hideOff) e.hidden = true; return; }
      const a = document.createElement("a");
      a.className = e.className + " open-live";
      a.href = base + e.dataset.console;
      a.target = "olli-ocp";
      a.rel = "noopener";
      a.textContent = e.dataset.label || e.textContent;
      e.replaceWith(a);
    });
    const start = parseInt((location.hash || "").replace("#", ""), 10);
    show(isNaN(start) ? 0 : start - 1);
  });
})();
