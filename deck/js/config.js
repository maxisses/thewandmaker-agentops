// Deck configuration. Everything on stage runs from this one file.
// mode "mock": all demos are scripted simulations that run inside the deck.
// mode "live": demos use the endpoints below where they are set, and fall back to the mock where they aren't.
window.OLLI_CONFIG = {
  mode: "mock",

  // Small "simulated" tag on mocked demo slides. Set to false to hide it.
  showSimBadge: true,

  // Logo files, by name. A plain path shows the logo next to the name.
  // { src, wordmark: true } shows the logo instead of the name (for logos that contain the name).
  // Empty = a dashed slot next to the name, or a drawn stand-in mark in the architecture picture.
  // Sources and licences: see assets/img/logos/SOURCES.md
  logos: {
    redclaw: "assets/img/logos/openclaw.svg",     // PLACEHOLDER: the OpenClaw lobster until there is a RedClaw logo
    openclaw: "assets/img/logos/openclaw.svg",
    openshell: "assets/img/logos/openshell.svg",
    mcp: "assets/img/logos/mcp-mark.svg",
    mlflow: { src: "assets/img/logos/mlflow.svg", wordmark: true },
    opentelemetry: "assets/img/logos/opentelemetry.svg",
    nemo: "", garak: "", midojo: "", evalhub: "",
    llmd: "assets/img/logos/llm-d.svg",
    vllm: "assets/img/logos/vllm.png",
    kserve: "assets/img/logos/kserve.svg",
    nemo_model: "assets/img/logos/models/nvidia-color.svg",
    gptoss: "assets/img/logos/models/openai.svg",
    gemma: "assets/img/logos/models/gemma-color.svg",
    llama: "assets/img/logos/models/meta-color.svg",
    granite: "assets/img/logos/models/ibm.svg",                 // PLACEHOLDER: the IBM logo, the set has no Granite icon
    mistral: "assets/img/logos/models/mistral-color.svg",
    deepseek: "assets/img/logos/models/deepseek-color.svg",
    qwen: "assets/img/logos/models/qwen-color.svg"
  },

  // Intro film. If the file is missing, the film slide shows a stepped animatic instead.
  filmSrc: "assets/video/intro.mp4",
  // The film has sounds but no voice. Set to false to play it silent.
  filmSound: true,

  // PLACEHOLDER: public URL of the audience shop (chapter 4). The QR code on the newspaper ad must
  // encode this URL. Until a real QR is generated, the deck draws a dummy pattern.
  audienceUrl: "olli.example/shop",
  audienceQrImage: "",          // e.g. "assets/img/qr.svg" once generated

  // Live endpoints. Leave empty to keep the mock. The real values for the cluster, and the desk
  // key, come from js/config.local.js, which "make deck-live" writes and which never goes into
  // git or the zip. With that file present the deck runs live; without it, it stays the mock.
  shopChatUrl: "",              // iframe URL of the real shop chat
  deskUrl: "",                  // iframe URL of the real master's desk (key added from config.local.js)
  consoleUrl: "",               // the apprentice's own console (OpenClaw Control UI), up after "make dashboard"
  mlflowTraceUrl: "",           // iframe URL of the MLflow trace view for the demo experiment
  campaignUrl: "",              // iframe URL of the EvalHub view for the red-team campaign
  rushStatsUrl: "",             // JSON endpoint with live rush counters
  consoleBase: ""               // the OpenShift console, for the links into it (topology, config maps)
};
