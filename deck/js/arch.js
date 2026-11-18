// The architecture picture: one drawing that transforms step by step.
// It starts as the prototype (every wire direct, every key in the digital apprentice's pocket) and each
// key press adds one thing. The new element shows up top left in red, travels to its place and
// settles in, while wires and keys move to match. Everything a chapter added stays red on that
// chapter's slide.
(function () {
  const CFG = window.OLLI_CONFIG || {};
  const STAGE = { x: 60, y: 24 };      // where a new element first appears (top left)
  const HOLD = 600;                    // ms it rests there
  const TRAVEL = 900;                  // ms it takes to reach its place

  // Each wire has a direct shape and a governed shape with the same number of points.
  // The governed shop wires share one start point, so a single line runs from the digital apprentice
  // to the tool gateway and fans out behind it.
  // `gate` names the feature that moves it from one to the other.
  const WIRES = {
    oracle: { d: [[627, 318], [1015, 251], [1430, 180]], g: [[627, 318], [1015, 180], [1430, 180]], gate: "modelgw" },
    cat: { d: [[630, 338], [1015, 330], [1430, 321]], g: [[628, 352], [1015, 380], [1430, 321]], gate: "toolgw" },
    nb: { d: [[630, 345], [1015, 366], [1430, 389]], g: [[628, 352], [1015, 380], [1430, 389]], gate: "toolgw" },
    led: { d: [[628, 352], [1015, 402], [1430, 457]], g: [[628, 352], [1015, 380], [1430, 457]], gate: "toolgw" },
    cab: { d: [[622, 372], [1015, 464], [1200, 508], [1430, 562]], g: [[628, 352], [1015, 380], [1015, 562], [1430, 562]], gate: "toolgw" }
  };
  // Keys start in the digital apprentice's pocket and dock on the gateway that takes them over.
  const KEYS = [
    { p: [690, 262], g: [926, 112], gate: "modelgw" },
    { p: [712, 300], g: [926, 312], gate: "toolgw" },
    { p: [718, 338], g: [974, 312], gate: "toolgw" },
    { p: [706, 378], g: [1022, 312], gate: "toolgw" },
    { p: [684, 414], g: [1070, 312], gate: "toolgw" }
  ];

  // What each architecture slide starts with, and what each key press adds.
  const CONTAIN = ["claw", "modelgw", "toolgw", "shell", "approval"];
  const SEE = ["taps", "scroll"];
  const TRUST = ["rails", "redteam"];
  const SEQ = {
    "s-arch0": { base: [], steps: [] },
    "s-arch1": { base: [], steps: CONTAIN },
    "s-arch2": { base: CONTAIN, steps: SEE },
    "s-arch3": { base: CONTAIN.concat(SEE), steps: TRUST },
    "s-arch4": { base: CONTAIN.concat(SEE, TRUST), steps: ["pool"] }
  };

  function boxInner(x, y, w, h, label, sub) {
    const cx = x + w / 2;
    const ly = sub ? y + h / 2 - 4 : y + h / 2 + 9;
    return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="14"/>' +
      '<text class="lbl' + (label.length > 22 ? " long" : "") + '" x="' + cx + '" y="' + ly + '" text-anchor="middle">' + label + "</text>" +
      (sub ? '<text class="sub" x="' + cx + '" y="' + (ly + 26) + '" text-anchor="middle">' + sub + "</text>" : "");
  }
  // key: the name live facts use to find this box (see FACTS below)
  function box(x, y, w, h, label, sub, cls, feat, key) {
    return '<g class="box ' + (cls || "") + (feat ? " f" : "") + '"' + (feat ? ' data-f="' + feat + '"' : "") +
      (key ? ' data-b="' + key + '"' : "") + ">" + boxInner(x, y, w, h, label, sub) + "</g>";
  }
  function tap(x, y) {
    return '<g class="tap"><circle cx="' + x + '" cy="' + y + '" r="13"/><circle class="pupil" cx="' + x + '" cy="' + y + '" r="5"/></g>';
  }
  function logoSrc(name) { const e = (CFG.logos || {})[name]; return e && (e.src || e); }
  function logo(src, x, y, size, fallback, disc) {
    if (!src) return fallback;
    // disc: a white plate under the logo, so it reads on the red apprentice
    return (disc ? '<circle cx="' + (x + size / 2) + '" cy="' + (y + size / 2) + '" r="' + (size / 2 + 6) + '" fill="#fbf4df"/>' : "") +
      '<image href="' + src + '" x="' + x + '" y="' + y + '" width="' + size + '" height="' + size + '"/>';
  }

  // Stand-in marks, drawn here until the real logo files are set in config.js.
  const clawMark = '<g fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round">' +
    '<path d="M545 312 Q536 340 541 368"/><path d="M566 306 Q560 340 565 374"/><path d="M588 312 Q584 340 590 368"/></g>';
  const shellMark = '<g transform="translate(372 222)"><path d="M17 0 L34 6 V18 C34 28 26 35 17 38 C8 35 0 28 0 18 V6 Z" fill="#151515"/>' +
    '<path d="M9 13 L15 18 L9 23 M18 24 H26" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g>';

  function buildSvg() {
    let wires = "";
    Object.keys(WIRES).forEach((k) => { wires += '<path class="wire" data-w="' + k + '"/>'; });
    let keys = "";
    KEYS.forEach((k, i) => {
      keys += '<g class="keyg" data-k="' + i + '"><circle class="key" cx="0" cy="0" r="9"/><path class="key" d="M9 0 h22 m-6 0 v8 m-8 -8 v6"/></g>';
    });
    return '<svg class="arch" viewBox="0 0 1800 880" xmlns="http://www.w3.org/2000/svg">' +
      // platform
      box(110, 782, 1580, 38, "Red Hat OpenShift AI", "", "soft", "", "ai") +
      box(40, 824, 1720, 42, "Red Hat OpenShift", "", "soft", "", "ocp") +
      // the OpenShell box around the digital apprentice
      '<g class="f shell" data-f="shell"><rect class="boundary" x="350" y="205" width="440" height="305" rx="26"/>' +
      logo(logoSrc("openshell"), 368, 216, 46, shellMark) +
      '<text class="lbl" x="420" y="250">OpenShell</text><text class="sub" data-b="shell" x="566" y="249"></text></g>' +
      // wires
      '<path class="wire" d="M260 365 L503 345"/>' + wires +
      '<g class="f" data-f="redteam" data-nofly="1"><path class="wire" d="M570 670 L570 530"/></g>' +
      // boxes
      box(40, 300, 220, 130, "Shop front", "chat UI", "", "", "shop") +
      box(900, 130, 230, 100, "Model gateway", "Models-as-a-Service", "", "modelgw", "modelgw") +
      box(900, 330, 230, 100, "Tool gateway", "MCP gateway", "", "toolgw", "toolgw") +
      box(1170, 130, 200, 100, "Guardrails", "NeMo, in and out", "", "rails", "rails") +
      '<g class="fnot" data-fnot="pool">' + box(1430, 130, 330, 100, "Oracle", "*you heard of it as LLM", "", "", "oracle") + "</g>" +
      '<g class="f box" data-f="pool"><rect class="stack" x="1454" y="146" width="330" height="100" rx="14"/><rect class="stack" x="1442" y="138" width="330" height="100" rx="14"/>' +
      boxInner(1430, 130, 330, 100, "Model pool on the AI platform", "llm-d · vLLM") + "</g>" +
      box(1430, 292, 330, 58, "Wand catalogue", "") +
      box(1430, 360, 330, 58, "The wand maker's notebooks", "") +
      box(1430, 428, 330, 58, "Ledger and reservations", "") +
      box(1140, 520, 240, 84, "Master's approval", "human in the loop", "", "approval", "approval") +
      box(1430, 520, 330, 84, "Locked cabinet", "restricted construction notes", "inkbox") +
      box(900, 670, 470, 96, "The day's scroll", "MLflow traces · OpenTelemetry · OpenShell audit", "", "scroll", "scroll") +
      box(40, 670, 770, 96, "Red Teaming before every new release", "Garak · MiDojo · EvalHub thresholds", "", "redteam", "redteam") +
      '<g class="f box" data-f="redteam" data-nofly="1">' + boxInner(470, 492, 200, 38, "release gate", "") + "</g>" +
      // keys
      keys +
      // the digital apprentice
      '<circle class="agent" cx="565" cy="340" r="62"/>' +
      '<path d="M565 300 Q571 334 605 340 Q571 346 565 380 Q559 346 525 340 Q559 334 565 300Z" fill="#fff"/>' +
      '<g class="f" data-f="claw"><circle class="agent" cx="565" cy="340" r="62"/>' + logo(logoSrc("redclaw"), 527, 302, 76, clawMark, true) + "</g>" +
      '<text class="lbl" x="565" y="448" text-anchor="middle">The digital apprentice</text>' +
      '<g class="f" data-f="claw" data-nofly="1"><text class="sub name" data-b="claw" x="565" y="474" text-anchor="middle">RedClaw</text></g>' +
      // eyes on the wires
      '<g class="f" data-f="taps">' + tap(820, 249) + tap(820, 366) + tap(1150, 180) + tap(1280, 386) + tap(1015, 480) + "</g>" +
      // one request travelling the wires (see REPLAY)
      '<g class="replay off"><path class="trail"/><circle class="pulse" r="14"/>' +
      '<g class="stopmark off"><circle r="21"/><path d="M-9 -9 L9 9 M9 -9 L-9 9"/></g>' +
      '<text class="leg" text-anchor="middle"></text><g class="kept"></g></g>' +
      // "live from the cluster" stamp, shown only when the picture carries live facts
      '<text class="livetag off" x="1760" y="752" text-anchor="end"></text>' +
      "</svg>";
  }

  function lerp(a, b, t) { return a + (b - a) * t; }
  function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

  function View(root) {
    root.innerHTML = buildSvg();
    this.root = root;
    this.gates = { modelgw: 0, toolgw: 0 };
    this.raf = 0;
    this.timers = [];
    this.paint();
  }
  View.prototype.paint = function () {
    const g = this.gates;
    Object.keys(WIRES).forEach((k) => {
      const w = WIRES[k], t = g[w.gate];
      const d = w.d.map((p, i) => (i ? "L" : "M") + lerp(p[0], w.g[i][0], t).toFixed(1) + " " + lerp(p[1], w.g[i][1], t).toFixed(1)).join(" ");
      this.root.querySelector('[data-w="' + k + '"]').setAttribute("d", d);
    });
    KEYS.forEach((k, i) => {
      const t = g[k.gate];
      this.root.querySelector('[data-k="' + i + '"]').setAttribute("transform",
        "translate(" + lerp(k.p[0], k.g[0], t).toFixed(1) + " " + lerp(k.p[1], k.g[1], t).toFixed(1) + ")");
    });
  };
  View.prototype.later = function (fn, ms) { this.timers.push(setTimeout(fn, ms)); };
  View.prototype.stop = function () {
    cancelAnimationFrame(this.raf);
    this.timers.forEach(clearTimeout);
    this.timers = [];
    this.root.querySelectorAll("[data-f]").forEach((e) => { e.style.transition = ""; e.style.transform = ""; });
  };
  View.prototype.moveGates = function (target, animate) {
    if (!animate) { this.gates = target; this.paint(); return; }
    const from = { modelgw: this.gates.modelgw, toolgw: this.gates.toolgw };
    const t0 = performance.now();
    const frame = (now) => {
      const t = Math.min(1, (now - t0) / TRAVEL), e = ease(t);
      this.gates = { modelgw: lerp(from.modelgw, target.modelgw, e), toolgw: lerp(from.toolgw, target.toolgw, e) };
      this.paint();
      if (t < 1) this.raf = requestAnimationFrame(frame);
    };
    this.raf = requestAnimationFrame(frame);
    // A hidden tab pauses animation frames. Land on the end state anyway.
    this.later(() => { cancelAnimationFrame(this.raf); this.gates = target; this.paint(); }, TRAVEL + 400);
  };
  // on: features that are on. red: features drawn in red (what this chapter added).
  // entering: the feature just added, which flies in from the top left. Null = jump to the state.
  View.prototype.set = function (on, red, entering) {
    const has = (f) => on.indexOf(f) >= 0;
    this.stop();
    this.root.classList.toggle("still", !entering);
    const target = { modelgw: has("modelgw") ? 1 : 0, toolgw: has("toolgw") ? 1 : 0 };
    const flyers = [], followers = [];
    this.root.querySelectorAll("[data-f]").forEach((e) => {
      const f = e.dataset.f;
      e.classList.toggle("new", red.indexOf(f) >= 0);
      if (entering && f === entering) { (e.dataset.nofly ? followers : flyers).push(e); return; }
      e.classList.toggle("off", !has(f));
    });
    this.root.querySelectorAll("[data-fnot]").forEach((e) => e.classList.toggle("off", has(e.dataset.fnot)));
    if (!entering) { this.moveGates(target, false); return; }

    // 1. appear top left
    flyers.forEach((e) => {
      const bb = e.getBBox();
      e.style.transition = "opacity .3s ease";
      e.style.transform = "translate(" + (STAGE.x - bb.x) + "px," + (STAGE.y - bb.y) + "px)";
      e.classList.remove("off");
    });
    // 2. travel to its place, while wires and keys move to match
    this.later(() => {
      flyers.forEach((e) => {
        e.style.transition = "transform " + TRAVEL + "ms cubic-bezier(.6,0,.2,1)";
        e.style.transform = "translate(0px,0px)";
      });
      this.moveGates(target, true);
    }, HOLD);
    // 3. settle: the parts that belong to it fade in
    this.later(() => { followers.forEach((e) => e.classList.remove("off")); }, HOLD + TRAVEL);
    this.later(() => { flyers.forEach((e) => { e.style.transition = ""; e.style.transform = ""; }); }, HOLD + TRAVEL + 500);
  };

  // ---------------------------------------------------------------------------------------------
  // Replays: one customer's request travels the wires, so the room sees which way a call takes
  // and where a refused call stops. Two extra key presses on the Contain picture, after the build.
  // The legs follow the governed wires (state after the five build steps). "stop" marks where a
  // leg ends for good: the OpenShell wall for the cabinet call, the master's desk for the request.
  // ---------------------------------------------------------------------------------------------
  const HOME = [565, 340], OUT = [628, 352];
  const there = (pts) => pts, back = (pts) => pts.slice().reverse();
  const ORACLE = [[627, 318], [1015, 180], [1430, 180]];
  const toShelf = (y) => [OUT, [1015, 380], [1430, y]];
  const REPLAY = {
    first: {
      legs: [
        { pts: [[260, 365], [503, 345], HOME], label: "the first-year asks", at: [200, 282] },
        { pts: there(ORACLE), label: "asks the oracle", at: [1015, 92] }, { pts: back(ORACLE) },
        { pts: there(toShelf(321)), label: "shop_catalogue_search", at: [1280, 276] }, { pts: back(toShelf(321)) },
        { pts: there(toShelf(389)), label: "shop_notebook_read", at: [1280, 276] }, { pts: back(toShelf(389)) },
        { pts: there(toShelf(457)), label: "shop_reserve_wand", at: [1280, 276] }, { pts: back(toShelf(457)) },
        { pts: [HOME, [503, 345], [260, 365]], label: "the answer goes back", at: [200, 282] }
      ]
    },
    boy: {
      legs: [
        { pts: [[260, 365], [503, 345], HOME], label: "the blond boy asks", at: [200, 282], bad: 1 },
        { pts: there(ORACLE), label: "asks the oracle", at: [1015, 92], bad: 1 }, { pts: back(ORACLE), bad: 1 },
        { pts: [OUT, [790, 364]], label: "shop_cabinet_open · refused by the policy", at: [1010, 468], bad: 1, stop: [790, 364], hold: 1400, keep: 1 },
        { pts: [[790, 364], OUT], bad: 1 },
        { pts: [OUT, [1015, 380], [1015, 562], [1140, 562]], label: "shop_cabinet_request · waits for the master", at: [1010, 640], park: 1, keep: 1 }
      ]
    }
  };
  const SPEED = 1500;   // px per second along a leg

  View.prototype.clearReplay = function () {
    this.replayGen = (this.replayGen || 0) + 1;
    this.replaying = false;
    const g = this.root.querySelector(".replay");
    g.classList.add("off");
    g.querySelector(".stopmark").classList.add("off");
    g.querySelector(".leg").textContent = "";
    g.querySelector(".kept").innerHTML = "";
    g.querySelector(".trail").setAttribute("d", "");
    if (this.sayEl) this.sayEl.classList.remove("on");
    if (this.legendEl) this.legendEl.classList.remove("on");
  };
  // Draw one leg at progress t (0 to 1): the pulse and its trail.
  View.prototype.paintLeg = function (leg, t) {
    const g = this.root.querySelector(".replay"), pts = leg.pts;
    let total = 0; const lens = [];
    for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); lens.push(l); total += l; }
    let rest = total * t, d = "M" + pts[0][0] + " " + pts[0][1], pos = pts[0];
    for (let i = 0; i < lens.length; i++) {
      if (rest >= lens[i]) { rest -= lens[i]; pos = pts[i + 1]; d += " L" + pos[0] + " " + pos[1]; continue; }
      const k = rest / lens[i];
      pos = [lerp(pts[i][0], pts[i + 1][0], k), lerp(pts[i][1], pts[i + 1][1], k)];
      d += " L" + pos[0].toFixed(1) + " " + pos[1].toFixed(1);
      break;
    }
    g.classList.toggle("bad", !!leg.bad);
    g.querySelector(".trail").setAttribute("d", d);
    const p = g.querySelector(".pulse");
    p.setAttribute("cx", pos[0].toFixed(1)); p.setAttribute("cy", pos[1].toFixed(1));
    return total;
  };
  // A leg's label travels with the replay; a label marked "keep" stays for the end state.
  View.prototype.legStart = function (leg) {
    const g = this.root.querySelector(".replay"), tx = g.querySelector(".leg");
    if (!leg.label) return;
    if (leg.keep) {
      tx.textContent = "";
      if (g.querySelector('.kept [data-l="' + leg.at.join("-") + '"]')) return;
      const k = document.createElementNS("http://www.w3.org/2000/svg", "text");
      k.setAttribute("class", "leg" + (leg.bad ? " no" : ""));
      k.setAttribute("text-anchor", "middle");
      k.setAttribute("x", leg.at[0]); k.setAttribute("y", leg.at[1]);
      k.dataset.l = leg.at.join("-");
      k.textContent = leg.label;
      g.querySelector(".kept").appendChild(k);
      return;
    }
    tx.textContent = leg.label;
    tx.setAttribute("x", leg.at[0]); tx.setAttribute("y", leg.at[1]);
  };
  View.prototype.legEnd = function (leg) {
    const g = this.root.querySelector(".replay");
    if (leg.stop) {
      const m = g.querySelector(".stopmark");
      m.setAttribute("transform", "translate(" + leg.stop[0] + " " + leg.stop[1] + ")");
      m.classList.remove("off");
    }
  };
  // Where a replay rests when it is over: the last label, the stop mark, the pulse parked or gone.
  View.prototype.finishReplay = function (name) {
    const r = REPLAY[name], g = this.root.querySelector(".replay");
    r.legs.forEach((leg) => { this.legStart(leg); this.legEnd(leg); });
    const last = r.legs[r.legs.length - 1];
    this.paintLeg(last, 1);
    g.querySelector(".trail").setAttribute("d", "");
    g.querySelector(".pulse").style.opacity = last.park ? 1 : 0;
    this.replaying = false;
  };
  View.prototype.replay = function (name) {
    const r = REPLAY[name];
    this.clearReplay();
    const gen = this.replayGen, g = this.root.querySelector(".replay");
    g.classList.remove("off");
    g.querySelector(".pulse").style.opacity = 1;
    // No caption above the picture: the moving request and its labels tell it (Max, 15 November).
    if (this.sayEl && r.say) { this.sayEl.textContent = r.say; this.sayEl.classList.add("on"); }
    // The legend: which colour is whose request; the running one stands out.
    if (this.legendEl) {
      this.legendEl.classList.add("on");
      this.legendEl.querySelectorAll("[data-who]").forEach((e) => e.classList.toggle("now", e.dataset.who === name));
    }
    this.replaying = true;
    this.replayName = name;
    let i = 0, t0 = performance.now(), len = 0, holding = false;
    const startLeg = () => { this.legStart(r.legs[i]); len = this.paintLeg(r.legs[i], 0); t0 = performance.now(); holding = false; };
    startLeg();
    const frame = (now) => {
      if (gen !== this.replayGen || !this.replaying) return;
      const leg = r.legs[i], dur = Math.max(160, 1000 * len / SPEED);
      if (!holding) {
        const t = Math.min(1, (now - t0) / dur);
        this.paintLeg(leg, ease(t));
        if (t < 1) { requestAnimationFrame(frame); return; }
        this.legEnd(leg);
        holding = true; t0 = now;
      }
      if (now - t0 < (leg.hold || 140)) { requestAnimationFrame(frame); return; }
      i++;
      if (i >= r.legs.length) { this.finishReplay(name); return; }
      startLeg();
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
    // A hidden tab pauses animation frames. Land on the end state anyway.
    let ms = 0;
    r.legs.forEach((leg) => {
      let l = 0;
      for (let k = 1; k < leg.pts.length; k++) l += Math.hypot(leg.pts[k][0] - leg.pts[k - 1][0], leg.pts[k][1] - leg.pts[k - 1][1]);
      ms += Math.max(160, 1000 * l / SPEED) + (leg.hold || 140);
    });
    setTimeout(() => { if (gen === this.replayGen && this.replaying) this.finishReplay(name); }, ms + 1500);
  };
  View.prototype.hurryReplay = function () { if (this.replaying) this.finishReplay(this.replayName); };

  // ---------------------------------------------------------------------------------------------
  // Live facts: in live mode every box says one thing the running platform reports right now.
  // The shop serves them at /api/platform: versions written at install time, counters it has
  // anyway. A box without a fact keeps the label it has in the scripted deck.
  // ---------------------------------------------------------------------------------------------
  const PLATFORM_URL = CFG.mode === "live" ? (CFG.platformUrl || (CFG.shopOrigin ? CFG.shopOrigin + "/api/platform" : "")) : "";
  const has = (v) => v !== undefined && v !== null && v !== "";
  const join = (parts) => parts.filter(has).join(" · ");
  const n = (v, one, many) => (has(v) ? v + " " + (v === 1 ? one : many) : "");
  // What each box says. f: fixed facts (versions), l: live counters. Missing values drop out.
  const FACTS = {
    shop: (f, l) => n(l.turnsToday, "turn today", "turns today"),
    claw: (f, l) => join([f.openclaw && "OpenClaw " + f.openclaw, n(l.sandboxes, "sandbox running", "sandboxes running")]),
    shell: (f, l) => join([f.openshell, has(l.refusedToday) ? l.refusedToday + " refused" : ""]),
    modelgw: (f, l) => n(l.modelCalls, "model call", "model calls"),
    // A stage name (Max, 17 November): before chapter 4 the oracle is "a local LLM", whatever
    // really answers behind the gateway (make oracle says which). Chapter 4 then moves it onto
    // the AI platform.
    oracle: (f, l) => join(["local LLM", n(l.modelCalls, "call", "calls")]),
    toolgw: (f, l) => join(["MCP gateway", n(l.tools, "tool", "tools")]),
    rails: (f, l) => (l.rails ? join([l.rails.release, has(l.rails.steppedIn) ? "caught " + l.rails.steppedIn : ""]) : ""),
    approval: (f, l) => (l.requests ? join([l.requests.filed + " asked", l.requests.declined + " declined"]) : ""),
    scroll: (f, l) => join([f.mlflow && "MLflow " + f.mlflow, n(l.tracesToday, "trace", "traces"), n(l.refusedToday, "refusal", "refusals")]),
    redteam: (f, l) => (l.campaign ? "our campaign runner · " + join([l.campaign.release, l.campaign.attacks + " attacks, " + l.campaign.held + " held"]) : "")
  };
  // The two platform bars carry their version in the label itself.
  const BARS = { ai: (f) => f.openshiftAi && "Red Hat OpenShift AI " + f.openshiftAi, ocp: (f) => f.openshift && "Red Hat OpenShift " + f.openshift };   // no "ROSA, region": beside the point on stage

  View.prototype.facts = function (d) {
    const f = (d && d.facts) || {}, l = (d && d.live) || {};
    let any = false;
    Object.keys(FACTS).forEach((key) => {
      const e = this.root.querySelector('[data-b="' + key + '"]');
      const t = e && (e.matches("text") ? e : e.querySelector(".sub"));
      if (!t) return;
      if (t.dataset.mock === undefined) t.dataset.mock = t.textContent;
      let line = "";
      try { line = FACTS[key](f, l) || ""; } catch (err) { line = ""; }
      t.classList.toggle("live", !!line);
      if (line) { t.innerHTML = '<tspan class="dot">● </tspan>' + line.replace(/&/g, "&amp;").replace(/</g, "&lt;"); any = true; }
      else t.textContent = key === "shell" ? "" : t.dataset.mock;
      // A line longer than its box is squeezed to fit, never left hanging over the edge.
      const rect = e.matches("text") ? null : e.querySelector("rect");
      t.removeAttribute("textLength");
      t.removeAttribute("lengthAdjust");
      const room = rect ? +rect.getAttribute("width") - 22 : 0;
      if (line && room > 0 && t.getComputedTextLength && t.getComputedTextLength() > room) {
        t.setAttribute("textLength", room);
        t.setAttribute("lengthAdjust", "spacingAndGlyphs");
      }
    });
    Object.keys(BARS).forEach((key) => {
      const t = this.root.querySelector('[data-b="' + key + '"] .lbl');
      if (!t) return;
      if (t.dataset.mock === undefined) t.dataset.mock = t.textContent;
      t.textContent = BARS[key](f) || t.dataset.mock;
    });
    const tag = this.root.querySelector(".livetag");
    tag.classList.toggle("off", !any);
    if (any) tag.innerHTML = '<tspan class="dot">● </tspan>live from the cluster · ' + new Date().toTimeString().slice(0, 8);
  };
  let factsTimer = 0;
  function watchFacts(view) {
    clearInterval(factsTimer);
    if (!PLATFORM_URL || Deck.mock("arch")) return;
    const pull = async () => {
      try { const r = await fetch(PLATFORM_URL, { cache: "no-store" }); if (r.ok) view.facts(await r.json()); } catch (e) { /* keep what is there */ }
    };
    pull();
    factsTimer = setInterval(pull, 5000);
  }

  window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".archwrap").forEach((wrap) => {
      const slide = wrap.closest(".slide");
      const seq = SEQ[slide.id] || { base: [], steps: [] };
      const view = new View(wrap);
      wrap.olliView = view;   // for rehearsals: wrap.olliView.facts({...}) in the browser console
      view.set(seq.base, [], null);
      // Replays run on the Contain picture, after its build steps. Their sentence sits above the picture.
      const replays = slide.id === "s-arch1" ? ["first", "boy"] : [];
      if (replays.length) {
        view.sayEl = document.createElement("div");
        view.sayEl.className = "arch-say";
        slide.appendChild(view.sayEl);
        view.legendEl = document.createElement("div");
        view.legendEl.className = "arch-legend";
        view.legendEl.innerHTML = '<span data-who="first"><i class="dot gold"></i>the first-year\'s request</span>' +
          '<span data-who="boy"><i class="dot red"></i>the blond boy\'s request</span>';
        slide.appendChild(view.legendEl);
      }
      // Live deck: one switch for all the pictures. Scripted, the boxes carry their written labels.
      const sw = PLATFORM_URL && seq.steps.length
        ? Deck.liveSwitch(slide, "arch", null, (mock) => { if (mock) { clearInterval(factsTimer); view.facts({}); } else watchFacts(view); })
        : null;
      Deck.register(slide.id, {
        steps: seq.steps.length + replays.length,
        // Live facts belong to the pictures of the platform, not to the prototype before it.
        enter() {
          view.clearReplay(); view.set(seq.base, [], null);
          if (sw) sw.paint();
          if (seq.steps.length) { if (Deck.mock("arch")) view.facts({}); watchFacts(view); }
        },
        step(n) {
          if (n > seq.steps.length) {
            if (n === seq.steps.length + 1) view.set(seq.base.concat(seq.steps), seq.steps, null);
            view.replay(replays[n - seq.steps.length - 1]);
            return;
          }
          const added = seq.steps.slice(0, n);
          view.set(seq.base.concat(added), added, seq.steps[n - 1]);
        },
        leave() { view.clearReplay(); view.stop(); clearInterval(factsTimer); },
        busy() { return !!view.replaying; },
        hurry() { view.hurryReplay(); }
      });
      // A deck opened straight on this slide showed it before this handler existed: start the facts now.
      if (slide.classList.contains("active") && seq.steps.length) watchFacts(view);
    });
  });
})();
