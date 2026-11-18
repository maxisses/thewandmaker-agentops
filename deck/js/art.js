// Illustrations: a look through an arched shop window into the candle-lit shop.
// Flat, original drawings. No film stills, no likenesses, no franchise artwork.
(function () {
  const INK = "#1a100a", GOLD = "#c9a24a", GOLD_L = "#ecd28a", RED = "#b3202a", CREAM = "#f6ecd2";
  let uid = 0;
  function rng(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }

  // The arched window every indoor scene sits in. `night` cools the light down.
  function windowFrame(inner, night) {
    const id = "w" + (++uid);
    const arch = "M70 880 L70 340 Q70 70 430 46 Q790 70 790 340 L790 880 Z";
    const stops = night
      ? '<stop offset="0" stop-color="#3b4a66"/><stop offset=".55" stop-color="#2a2a3a"/><stop offset="1" stop-color="#17100b"/>'
      : '<stop offset="0" stop-color="#f7d488"/><stop offset=".5" stop-color="#cf8f3a"/><stop offset="1" stop-color="#4a2a12"/>';
    return '<defs><linearGradient id="' + id + 'g" x1="0" y1="0" x2="0" y2="1">' + stops + "</linearGradient>" +
      '<radialGradient id="' + id + 'r" cx=".5" cy=".42" r=".6"><stop offset="0" stop-color="#fff2c4" stop-opacity="' + (night ? ".10" : ".55") + '"/><stop offset="1" stop-color="#fff2c4" stop-opacity="0"/></radialGradient>' +
      '<clipPath id="' + id + 'c"><path d="' + arch + '"/></clipPath></defs>' +
      '<path d="' + arch + '" fill="url(#' + id + 'g)"/>' +
      '<g clip-path="url(#' + id + 'c)"><rect x="70" y="40" width="720" height="840" fill="url(#' + id + 'r)"/>' + inner + "</g>" +
      '<path d="' + arch + '" fill="none" stroke="#0d0805" stroke-width="26"/>' +
      '<path d="' + arch + '" fill="none" stroke="' + GOLD + '" stroke-width="6"/>' +
      '<path d="M430 46 V880 M70 470 H790" stroke="#0d0805" stroke-width="10" opacity=".55"/>' +
      '<rect x="40" y="868" width="780" height="26" rx="6" fill="#0d0805"/><rect x="40" y="868" width="780" height="5" fill="' + GOLD + '"/>';
  }

  // Shelves of wand boxes in dark jewel colours, each with a small gold label.
  function shelf(x, y, w, rows, seed) {
    const r = rng(seed);
    const fills = ["#5e1a22", "#2c4636", "#26324a", "#4a3120", "#3a2418", "#6b4a1e", "#2a1b12"];
    let out = "";
    for (let i = 0; i < rows; i++) {
      let cx = x;
      const ry = y + i * 50;
      while (cx < x + w - 50) {
        const bw = Math.min(60 + Math.floor(r() * 110), x + w - cx);
        const f = fills[Math.floor(r() * fills.length)];
        out += '<rect x="' + cx + '" y="' + ry + '" width="' + (bw - 7) + '" height="38" rx="4" fill="' + f + '"/>' +
          '<rect x="' + (cx + 8) + '" y="' + (ry + 13) + '" width="16" height="12" rx="2" fill="' + GOLD + '" opacity=".85"/>';
        cx += bw;
      }
      out += '<rect x="' + x + '" y="' + (ry + 40) + '" width="' + w + '" height="6" fill="#120b07"/>';
    }
    return out;
  }

  function spark(x, y, s) {
    return '<g transform="translate(' + x + " " + y + ") scale(" + s + ')">' +
      '<circle r="104" fill="#ffe7a8" opacity=".28"/><circle r="66" fill="#fff3cf" opacity=".35"/>' +
      '<path d="M0 -60 Q9 -9 60 0 Q9 9 0 60 Q-9 9 -60 0 Q-9 -9 0 -60Z" fill="' + RED + '"/>' +
      '<circle r="86" fill="none" stroke="' + GOLD_L + '" stroke-width="3" stroke-dasharray="3 13"/></g>';
  }
  function star(x, y, s, fill) {
    return '<path transform="translate(' + x + " " + y + ") scale(" + s + ')" d="M0 -10 Q1.5 -1.5 10 0 Q1.5 1.5 0 10 Q-1.5 1.5 -10 0 Q-1.5 -1.5 0 -10Z" fill="' + (fill || GOLD_L) + '"/>';
  }
  function candle(x, y, h) {
    return '<circle cx="' + x + '" cy="' + (y - h - 14) + '" r="54" fill="#ffd77a" opacity=".30"/>' +
      '<rect x="' + (x - 9) + '" y="' + (y - h) + '" width="18" height="' + h + '" rx="3" fill="' + CREAM + '"/>' +
      '<ellipse cx="' + x + '" cy="' + (y - h - 14) + '" rx="7" ry="14" fill="#ffcf5a"/><ellipse cx="' + x + '" cy="' + (y - h - 10) + '" rx="3" ry="7" fill="#fff6d8"/>';
  }
  // The wandmaker from behind: long coat, wild pale hair.
  function wandmaker(x, y, s) {
    return '<g transform="translate(' + x + " " + y + ") scale(" + s + ')">' +
      '<path d="M-96 300 L-78 44 Q0 -14 78 44 L96 300Z" fill="' + INK + '"/><circle cx="0" cy="-34" r="48" fill="' + INK + '"/>' +
      '<g fill="#e3d6b6"><ellipse cx="-44" cy="-52" rx="22" ry="14" transform="rotate(-30 -44 -52)"/><ellipse cx="44" cy="-52" rx="22" ry="14" transform="rotate(30 44 -52)"/>' +
      '<ellipse cx="-54" cy="-22" rx="18" ry="11" transform="rotate(-70 -54 -22)"/><ellipse cx="54" cy="-22" rx="18" ry="11" transform="rotate(70 54 -22)"/><ellipse cx="0" cy="-76" rx="26" ry="12"/></g></g>';
  }
  // A first-year: pointed hat, striped scarf.
  function firstYear(x, y, s) {
    return '<g transform="translate(' + x + " " + y + ") scale(" + s + ')">' +
      '<path d="M-62 220 L-48 30 Q0 0 48 30 L62 220Z" fill="' + INK + '"/><circle cx="0" cy="-22" r="38" fill="' + INK + '"/>' +
      '<path d="M-52 -40 L0 -150 L52 -40Z" fill="' + INK + '"/>' +
      '<rect x="-46" y="14" width="92" height="20" rx="8" fill="' + RED + '"/><rect x="-22" y="14" width="14" height="20" fill="' + GOLD + '"/><rect x="14" y="14" width="14" height="20" fill="' + GOLD + '"/>' +
      '<rect x="18" y="28" width="20" height="74" rx="8" fill="' + RED + '"/><rect x="18" y="56" width="20" height="12" fill="' + GOLD + '"/></g>';
  }
  // The blond boy: sleek pale hair, arms crossed.
  function blondBoy(x, y, s) {
    return '<g transform="translate(' + x + " " + y + ") scale(" + s + ')">' +
      '<path d="M-62 220 L-48 30 Q0 0 48 30 L62 220Z" fill="' + INK + '"/><circle cx="0" cy="-22" r="38" fill="' + INK + '"/>' +
      '<path d="M-40 -30 Q-44 -70 0 -66 Q44 -70 40 -30 Q20 -50 -6 -44 Q-24 -42 -40 -30Z" fill="#efe6c4"/>' +
      '<path d="M-50 92 L50 70 M-50 70 L50 92" stroke="#2f4a38" stroke-width="8" stroke-linecap="round"/></g>';
  }
  function counter(y) {
    return '<rect x="40" y="' + y + '" width="780" height="34" fill="#120b07"/><rect x="40" y="' + y + '" width="780" height="5" fill="' + GOLD + '" opacity=".8"/>' +
      '<rect x="40" y="' + (y + 34) + '" width="780" height="320" fill="#1d120b"/>' +
      '<rect x="110" y="' + (y + 70) + '" width="640" height="150" rx="6" fill="none" stroke="#3a2616" stroke-width="5"/>';
  }
  function scroll(x, y) {
    let lines = "";
    for (let i = 0; i < 9; i++) {
      lines += '<rect x="' + (x + 26) + '" y="' + (y + 40 + i * 34) + '" width="' + (150 + ((i * 53) % 90)) + '" height="7" rx="3" fill="' + (i === 5 ? RED : "#8a744a") + '"/>';
    }
    return '<rect x="' + x + '" y="' + y + '" width="300" height="380" rx="6" fill="#f3e7ca"/>' +
      '<rect x="' + (x - 14) + '" y="' + (y - 16) + '" width="328" height="32" rx="16" fill="#8a6a2e"/>' + lines;
  }

  const scenes = {
    shop: () => windowFrame(shelf(80, 100, 700, 9, 7) + candle(690, 640, 70) + wandmaker(270, 400, 1) + spark(540, 440, 0.8) + counter(640)),
    first: () => windowFrame(shelf(80, 100, 700, 9, 7) + candle(130, 640, 60) + wandmaker(250, 400, 0.95) + spark(470, 430, 0.8) + counter(640) + firstYear(650, 620, 1.2)),
    boy: () => windowFrame(shelf(80, 100, 700, 9, 7) + spark(320, 430, 0.8) + counter(640) + blondBoy(630, 620, 1.2)),
    night: () => windowFrame(shelf(80, 100, 700, 9, 11) + star(190, 150, 1.6) + star(660, 210, 1.1) + star(560, 120, 0.8) +
      scroll(440, 300) + candle(390, 700, 80) + wandmaker(240, 440, 1.1) + spark(690, 240, 0.5) + counter(700), true),
    afternoon: () => windowFrame(
      shelf(80, 100, 700, 7, 23) + spark(640, 400, 0.7) + counter(560) +
      // armchair from behind, the wandmaker's hair just showing, a cup of tea on a side table
      '<g transform="translate(300 600)"><path d="M-130 250 L-130 -40 Q-130 -150 0 -150 Q130 -150 130 -40 L130 250Z" fill="#4a1a20"/>' +
      '<path d="M-150 250 L-150 60 Q-150 20 -118 20 L-118 250Z M150 250 L150 60 Q150 20 118 20 L118 250Z" fill="#3a1418"/>' +
      '<g fill="#e3d6b6"><ellipse cx="-30" cy="-168" rx="24" ry="13" transform="rotate(-20 -30 -168)"/><ellipse cx="26" cy="-170" rx="24" ry="13" transform="rotate(18 26 -170)"/><ellipse cx="0" cy="-182" rx="22" ry="11"/></g></g>' +
      '<g transform="translate(560 720)"><rect x="-70" y="0" width="140" height="12" rx="4" fill="#120b07"/><rect x="-8" y="12" width="16" height="150" fill="#120b07"/>' +
      '<path d="M-26 -34 H26 L20 0 H-20Z" fill="' + CREAM + '"/><path d="M26 -26 Q46 -24 40 -8 Q36 0 22 -4" fill="none" stroke="' + CREAM + '" stroke-width="6"/>' +
      '<path d="M-10 -48 Q-22 -66 -8 -80 M8 -50 Q-2 -70 12 -88" fill="none" stroke="' + CREAM + '" stroke-width="4" stroke-linecap="round" opacity=".7"/></g>' +
      candle(150, 560, 60)),
    // Red teaming: the second oracle (dark) throws attacks at the apprentice behind his guardrails.
    spar: () => {
      const C = [600, 560], R = 190, A = [170, 250];
      let out = '<g transform="translate(' + A[0] + " " + A[1] + ')"><circle r="120" fill="#6a7fb0" opacity=".14"/>' +
        '<path d="M0 -70 Q10 -10 70 0 Q10 10 0 70 Q-10 10 -70 0 Q-10 -10 0 -70Z" fill="#0b0705" stroke="#8fa0c8" stroke-width="4"/></g>' +
        '<circle cx="' + C[0] + '" cy="' + C[1] + '" r="' + R + '" fill="rgba(201,162,74,.07)" stroke="' + GOLD + '" stroke-width="5" stroke-dasharray="16 12"/>' + spark(C[0], C[1], 1.0);
      const base = Math.atan2(A[1] - C[1], A[0] - C[0]);
      [-2, -1, 0, 1, 2].forEach((i) => {
        const a = base + i * 0.3;
        const px = C[0] + R * Math.cos(a), py = C[1] + R * Math.sin(a);
        const sx = A[0] + 80 + i * 26, sy = A[1] + 50 - i * 34;
        if (i === 1) {
          const ex = C[0] + 82 * Math.cos(a), ey = C[1] + 82 * Math.sin(a);
          out += '<path d="M' + sx + " " + sy + " L" + ex.toFixed(0) + " " + ey.toFixed(0) + '" stroke="#e2574c" stroke-width="6" stroke-linecap="round" fill="none"/>' +
            '<circle cx="' + ex.toFixed(0) + '" cy="' + ey.toFixed(0) + '" r="11" fill="#e2574c"/>';
        } else {
          const tx = -Math.sin(a) * 20, ty = Math.cos(a) * 20;
          out += '<path d="M' + sx + " " + sy + " L" + px.toFixed(0) + " " + py.toFixed(0) + '" stroke="' + CREAM + '" stroke-width="5" stroke-linecap="round" stroke-dasharray="2 12" fill="none" opacity=".8"/>' +
            '<path d="M' + (px - tx).toFixed(0) + " " + (py - ty).toFixed(0) + " L" + (px + tx).toFixed(0) + " " + (py + ty).toFixed(0) + '" stroke="' + GOLD_L + '" stroke-width="8" stroke-linecap="round"/>';
        }
      });
      return out + star(330, 640, 1.4) + star(760, 240, 1.0) + star(120, 520, 0.9);
    }
  };

  window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("svg[data-scene]").forEach((el) => {
      const fn = scenes[el.dataset.scene];
      if (fn) el.innerHTML = fn();
    });
  });
})();
