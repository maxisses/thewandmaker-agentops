# Talk notes, state of 16 November 2026

> This was the project README until 18 November 2026. It describes the deck and the demos as they
> were the day before the talk; slide numbers moved by one since (slide 1 is now the backstage
> guide). For building the platform, start with [AGENTS.md](../AGENTS.md).


> **Changed on 16 November, afternoon. Read this first; the text below it still uses the old names and numbers in places.**
>
> - On stage the agent is "the digital apprentice", the shop is "The Wand Shop" and its owner is "the wand maker". "Hogwarts", "Quidditch" and "The Daily Prophet" are gone from the deck, the shop pages, the persona, the rails and the tool texts. "You-Know-Who" stays (Max's call). Technical names stay too: the namespace `ollivanders`, the sandboxes `apprentice`, `apprentice-2`, `apprentice-3`, the MLflow experiment `apprentice`.
> - The deck has 28 slides. New slide 4 welcomes the digital apprentice (the red wisp). The translation table is gone. The close ("took the afternoon off") now comes before the summary, which is called "AgentOps". (The scroll demo was taken out by mistake for an hour on 16 November and is back as slide 13.)
>
> | Slides | What |
> |---|---|
> | 1 to 6 | curtain, film, title, welcome, the prototype (with a link to the topology view), four questions |
> | 7 to 11 | Contain: chapter card, demo 1, the console, the picture, inside OpenShell |
> | 12 to 14 | See: chapter card, demo 2 (the day's scroll, with the visit in MLflow), the picture |
> | 15 to 20 | Trust: chapter card, demo 3, the rails in OpenShift AI, the second oracle, the campaign, the picture |
> | 21 to 24 | Scale: the newspaper, the rush, the inference stack, the picture |
> | 25 to 28 | the close, AgentOps, six layers, thanks |
>
> - The phone page is a plain chat. The shop hands every phone a made-up wizard's name (`rush.py`, `wizard()`); there are no buttons for a first-year or the blond boy any more. The task ("get the name out of him") is said on stage. The name is written in full nowhere; the campaign's leak shows three letters.
> - The sales ledger now carries the name the buyer took later, so that is what the red-team campaign gets out of release 1.5.
> - In live mode every demo slide (8, 13, 16, 19, 22) and the pictures carry a switch, bottom left, and the key M: live or scripted.
> - Links into the OpenShift console (topology on slide 5, the rails' config map on slides 16 and 19) need `make deck-live` (it writes `consoleBase`) and a console login in the same browser.
> - `make up-persona` gives running apprentices changed persona files without recreating them. `make links` prints every address (`SECRETS=1` adds the desk key and the password).
> - In MLflow, do not open the blond boy's trace on stage: MLflow shows the name unredacted. Traces from before the afternoon of 16 November still say "Mr Ollivander".

Talk and demo for "Operate your agents – safely!". Twenty minutes, for product teams.

Mr Ollivander can't find an apprentice, so he hires an AI one. Then four questions keep him awake:
can I limit what it can do, can I see what it did, can I trust it to ship, and can it handle the
back-to-school rush?

## What is in this folder

| Path | What it is |
|---|---|
| `STORYLINE.md` | The agreed flow, the cast, the media plan and the run of show |
| `RESEARCH.md` | What the platform really offers today, matched against the story, with sources |
| `deck/` | The presentation app: slides, film, architecture picture and the demos in one page |
| `film/` | The intro film: the generated shots and sounds, `film/cut.py` that cuts them, and the result in `film/renders/` |
| `gitops/` | The platform on the cluster, one folder per piece, in install order; `make up-platform` runs them all |
| `apps/shop/` | The shop: tools (MCP), chat, desk, scroll, rails, campaign and phone pages, model gateway |
| `scripts/` | Cluster access and login, bastion runner, deck live switch, captures of real product pages, night run, campaign, simulated audience |
| `docs/build-journal.md` | What we built, what bit us, the numbers, and the checklist before the talk |

## Run the deck

```bash
python3 -m http.server 8765 --directory deck
```

Then open http://127.0.0.1:8765 in a browser and press F for fullscreen.

| Key | Does |
|---|---|
| Right arrow, Space, Page Down | Next step, then next slide |
| Left arrow, Page Up | Back |
| N | Speaker notes |
| R | Restart the current slide |
| F | Fullscreen |

A presenter remote that sends Page Up and Page Down works. While a demo beat is still playing, the
next key finishes that beat at once, so you can never get stuck behind an animation.

## What is real and what is simulated

`deck/js/config.js` has `mode: "mock"`: every demo is scripted. With `make deck-live` all live
demos run against the cluster (see `docs/build-journal.md`); without the cluster, the deck falls
back to the scripted version.

| Slide | Live (`make deck-live`) | Mock |
|---|---|---|
| Intro film | Photorealistic, 13 shots, 70 seconds, generated with Higgsfield (Kling 3.0). Sounds that fit the action (rain, paper, typing, keys, owls), also generated; no voice and no music, because the presenter speaks over it. Script in `film/VIDEO_SCRIPT.md`, clips in `film/generated/`. | same |
| Chapter cards, architecture picture, newspaper, wrap-up | Drafts. The newspaper shows the real QR code and the live number of first-years in the shop. | dummy QR |
| OpenShell policy slide | An excerpt of the real policy (`gitops/04-openclaw/policy.yaml`) | same |
| Demo 1, shop chat and master's desk | Real apprentice (OpenClaw in OpenShell), real desk | scripted |
| The apprentice's own console | A capture of the real OpenClaw Control UI from the cluster (`make captures`), with the blond boy's session and its failed tool call. The console forbids frames, so it can't be shown live inside the deck; `make dashboard` opens it in a browser tab. | the same capture if there is one, else a sketch that says so |
| Demo 2, the day's scroll | Real traces from MLflow, refusals from OpenShell's audit log, the night's visits from `make night`. One click shows the same visit in MLflow's own page, as a capture from the cluster. | scripted, modelled on the MLflow trace view, with a tryout room |
| Demo 3, shop front and guardrail counters | Real chat, NeMo Guardrails in the model path, real counters, each with its rail's real name | scripted |
| Where the rails live | The deployed `NemoGuardrails` resource on its page in the OpenShift console, as a capture (`make captures`, you log in to the console once) | a sketch of the page, and it says so |
| Six layers (slide 27) | The shop measured against Red Hat's e-book "Defense in depth for agentic AI", with a QR code to it. Four layers are there, one is half there, one is not built, and the slide says which. | same |
| Architecture picture | Under every box one line from the running cluster (versions, calls, refusals, what the rails caught), refreshed every five seconds. On the Contain picture two requests travel the wires. | the same picture without the live lines |
| Red-team campaign | Real campaigns against rails 1.5 and 1.5.1 (`make campaign`), replayed from MLflow. Our own campaign runner, not Garak. | scripted |
| Inference stack | Names and two numbers taken from a Red Hat slide, not checked again | same |
| Demo 4, the rush | Real counters from the audience's phones, three bars for the three apprentices, the real phone page, real 429 count from MaaS. The last step is an illustration and says so. | simulated counters |

Mocked slides carry a small "simulated" tag. Set `showSimBadge: false` in the config to hide it.

The architecture picture is one drawing that transforms: it starts as the prototype and every key
press adds one thing, so wires and keys move to their new place. On the Contain picture two more
key presses send a request along the wires: the first-year's goes out through the gateways and
comes back, the blond boy's cabinet call stops at the OpenShell wall. The slide after it zooms
into OpenShell and shows the shop's policy.

Three slides show a real product page as a capture, with the date it was taken in a bar on top:
the apprentice's console, a trace in MLflow, and the deployed guardrails in the OpenShift console.
None of the three lets another page frame it, which is why they are captures. `make captures`
takes them from the cluster.

## Placeholders still open

Each one is marked on its slide or in the speaker notes.

1. A picture of the real shop front with its window for the first slide. Parked until the film is redone.
2. Missing logos: Garak, NeMo Guardrails, EvalHub, MiDojo, Kagenti, a RedClaw logo (the OpenClaw lobster stands in) and a Granite logo (the IBM logo stands in). A missing logo shows as a dashed slot next to the name. Loaded logos and their sources are listed in `deck/assets/img/logos/SOURCES.md`; paths go into `logos` in `deck/js/config.js`.
3. Contact and repository on the last slide.
4. The restricted note itself, if we ever show an approved request.
5. The tryout room exists only in the mock of demos 1 and 2. The translation slide no longer mentions it.

## Going live

```bash
make cluster-login   # tokens last 24 hours
make deck-live       # writes deck/js/config.local.js: shop address and desk key, from the cluster
make captures        # real product pages for three slides (after demo 1 was played once)
make deck-mock       # removes config.local.js: back to the scripted version
make deck-zip        # zip for colleagues, always without config.local.js
```

`config.js` stays on `mock`, so the shared zip is always the scripted deck. `config.local.js` holds
the desk key; it is in `.gitignore` and never goes into the zip.

Before the talk:

1. Once, a day or more before: `make night` (the blond boy's visits for demo 2). Done on
   15 November. Don't repeat it: every run adds its visits to the night's count.
2. In the morning, at least an hour before the talk: `make campaign` (both releases, two turns at
   a time; Red Hat MaaS limits tokens per minute, so not right before the talk). When MaaS is
   locked or full, the model gateway sends calls to a backup oracle on OpenRouter, capped at
   3 US dollars. For now OpenRouter answers first and MaaS is the fallback (`ORACLE_MODE` in
   `gitops/20-shop/install.sh`); `make oracle` shows the mode and the spend. Since 16 November a second
   Red Hat endpoint (`REDHATTMM_*` in `.env`) is asked before both of them.
3. After a rehearsal of demo 1, any time before the talk: `make captures`. A Chrome window opens
   for the OpenShift console; log in there yourself, once.
4. Just before: "New day" on the desk, `python3 scripts/rush-sim.py --reset`, "Reset counters" on
   `/rails`. Open the deck from the first slide, so the live frames load in the background. If
   you want the apprentice's console live in a second tab: `make dashboard`.

The demos, live:

- Demo 1: four clicks, each puts one customer line into the real chat; answers take 5 to 20
  seconds, so keep talking. The blond boy's cabinet call turns up in red: "cabinet open · refused
  by the lock". Beat 3 declines on the desk (it waits for the request if it isn't there yet).
- The console (slide 8): the apprentice's own Control UI as a capture, with the blond boy's
  session and its failed cabinet call. One click shows the way in.
- The picture (slide 9): five clicks build it, two more send the first-year's and the blond boy's
  request along the wires. Live, every box carries a line from the cluster.
- Demo 2: six clicks through the scroll: the first-year's turn, one tool call, the same visit in
  MLflow, the blond boy's refused call with OpenShell's audit record and the decline, the night.
- Demo 3: German question (translated on the way out), Quidditch (stopped before the model),
  "say his name" (blacked out on the way out). Then the room's turn: type into the chat.
- Where the rails live (slide 16): the deployed guardrails on the cluster's own page, one click.
- Campaign: release 1.5 (one attack got through), the leak, the fix, release 1.5.1 (may ship).
- Demo 4: the audience scans the QR code on the newspaper and uses `/phone`. Three apprentices,
  eight customers at once, the rest queue. Beat 2 shows MaaS's real 429 count. In the model
  gateway's mode `overflow` the backup oracle takes the calls that would queue; mode `lock` keeps
  the queue (walkthrough, demo 4).

After a click inside a frame, the arrow keys and the remote still move the deck. That forwarding
is not tested with a real remote yet.

Other pages for the operator, all with the desk key in the fragment (`#key=…`): `/desk`,
`/scroll`, `/rails`, `/campaign`. The MLflow UI is in the OpenShift AI dashboard under MLflow,
workspace ollivanders. The apprentice's own console, OpenClaw's Control UI from inside the
sandbox, opens with `make dashboard` at http://127.0.0.1:18789 (through an OpenShell port
forward and an ssh tunnel; never on the cluster's edge). The numbers under the architecture
picture's boxes come from `/api/platform` on the shop, open and counts only.

## Rebuild the film

```bash
make film
```

That runs `film/cut.py --install`: it draws the on-screen text, lays it over the thirteen shots in
`film/generated/clips/v2/`, mixes the sounds listed in `film/sound.json`, writes
`film/renders/intro.mp4` and copies it to `deck/assets/video/intro.mp4`. It needs ffmpeg and
Pillow. Change a line of text in `TEXT` at the top of `film/cut.py`, change where a sound sits in
`film/sound.json`. To play the film silent, set `filmSound: false` in `deck/js/config.js`.

If the video file is missing, the film slide steps through the same six lines as an animatic. The
HyperFrames project in `film/` (`index.html`, `compositions/`) is the first, drawn cut and is no
longer what the deck shows.
