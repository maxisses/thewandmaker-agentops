// Shared by chat and desk when they sit inside the deck (URL has ?embed=1).
// - Larger type and no page header, because the deck panel has its own.
// - Navigation keys go back to the deck, so the presenter remote keeps working after a click in here.
// - The deck can send commands with postMessage ({type: "olli:..."}).
(function () {
  const params = new URLSearchParams(location.search);
  const embedded = params.get("embed") === "1" && window.parent !== window;
  const handlers = {};
  if (embedded) document.documentElement.classList.add("embed");

  if (embedded) {
    document.addEventListener("keydown", (e) => {
      const typing = /INPUT|TEXTAREA/.test((e.target && e.target.tagName) || "");
      const nav = ["PageDown", "PageUp"].includes(e.key) || (!typing && ["ArrowRight", "ArrowLeft", " "].includes(e.key));
      if (!nav) return;
      e.preventDefault();
      window.parent.postMessage({ type: "olli:key", key: e.key }, "*");
    });
  }
  window.addEventListener("message", (e) => {
    const m = e.data;
    if (!embedded || e.source !== window.parent || !m || typeof m.type !== "string") return;
    const h = handlers[m.type];
    if (h) h(m);
  });
  window.OlliEmbed = { embedded, on: (type, fn) => { handlers[type] = fn; } };
})();
