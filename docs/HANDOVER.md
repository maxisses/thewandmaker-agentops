# Addendum, 17 November 2026, evening: the deck on the cluster, backstage as slide 1

Read this before the rest; the slide numbers further down are from before (every slide moved by one).

- **The deck is served from the cluster.** `make up-deck` (`gitops/24-deck`) stages a copy of `deck/`,
  builds an httpd image on the cluster and puts it behind an HTTPS route, `deck-ollivanders.<apps domain>`.
  Without a key it is the scripted deck, open to everyone, speaker notes included. With the desk key in
  the link (`…/#key=…`, printed by `make links SECRETS=1`) it runs live; the browser keeps the key in
  its local storage, `…/#key=` forgets it. The key is in no file of the image; `install.sh` checks.
- **Slide 1 is backstage**, 29 slides now. Live it frames the shop's new page `/backstage`: the guide
  (logins, steps, keys, every address, what to do when something sticks) and three buttons.
  Prepare, Prepare with the night, Reset run inside shop-front (`apps/shop/shop/backstage.py`,
  `/api/backstage`, desk key). They do what `scripts/prepare.py` does, minus the cluster login, the
  console forward and the per-oracle key checks (the page asks the model gateway once instead).
  The gateways are restarted through the OpenShell CLI that shop-front already carries.
- **The cluster-admin password is not on that page**, on purpose: the desk key would then be worth the
  whole cluster. The page says where the password is.
- **The night's tricks** live in `apps/shop/shop/tricks.py` now; `scripts/night.py` reads them from there.
- After any change to the deck's files: `make up-deck`. After a change to the backstage page: `make up-shop`.

## Another cluster

Nothing in the code names this cluster. The shop reads its console and deck addresses from the
config map `shop-links`, which `gitops/20-shop/install.sh` fills from the cluster it is logged in
to; the hosted deck's config is written by `scripts/deck-live.py --hosted` from the shop's route.

1. `.env`: the new cluster's `ROSA_API_URL`, the bastion, the model endpoints and keys.
2. `make up` (the cluster), then `make up-platform`. It ends with `make up-deck`.
3. `make campaign` once (slide 20 replays the stored run). The night and everything else: the
   Prepare button on slide 1.
4. `make captures` with a console login, for the three screenshots that are baked into the deck
   (they show this cluster's pages until then), then `make up-deck` again.

Not tried on a second cluster. The namespaces (`ollivanders`, `openshell`) and the sandbox names
are the same everywhere by design.

---

# Handover, 15 November 2026, about 11:10

Written by the session that rebuilt the platform and moved the machinery into the deck, for the
session that takes over. The talk is on 17 November. Talk to Max in German; files are in English.
Read this first, then `docs/build-journal.md` (sections "Second build" and "The machinery moves
into the deck") and `docs/walkthrough.md` section 4.

## Where things stand

| Thing | State |
|---|---|
| Cluster `rosa-t4zm5` | Up, everything installed by `make up-platform`. Max says the lab's retirement date is extended. `make cluster-login` is due by 16 November 08:30. |
| Deck | Live mode (`deck/js/config.local.js` exists), served on port 8765. 27 slides, assets at `?v=31`. Mock mode still works (`make deck-mock`). |
| Demos 1, 2, 3, 4 | Checked live in the deck today, slide by slide. Not yet in one pass with Max at the keys. |
| Captures | `mlflow` (slide 12) and `console` (slide 8) taken. `guardrails` (slide 16) is missing: it needs Max's own login, see below. Until then slide 16 shows a sketch and says so. |
| Night run | Done today: 37 visits on the scroll, the lock said no 24 times. Do not run `make night` again; it would add to the count. |
| Campaign, release 1.5 | Good run at 11:00, in MLflow: name 11 of 12 (one spelled attack got through), 12 of 12 customers served, blocked. This is the story. |
| Campaign, release 1.5.1 | Clean run at 11:33 (after the handover): all rules held, 12 of 12 served, "may ship", MLflow run `e6bb842c6273469c8cea3c7382d322d8`. No 429, the backup oracle wasn't needed. |
| Docs | README, STORYLINE, walkthrough and build journal are updated for everything below. |
| Backup oracle | Done after the handover (see the last two sections): OpenRouter behind the model gateway, mode `overflow`, cap 3 US dollars, tested through the shop. |

## What changed today, in one list

- `make up-access`, wait points in `make up-platform` (by the build subagent).
- Deck: fourth question matches the film, tryout room row replaced, two requests travel the wires
  on the Contain picture (clicks 6 and 7), policy slide in three clicks, live lines under every
  architecture box (`/api/platform`), MLflow capture as click 3 of demo 2, new slide 16 "where the
  rails live", rail names in demo 3, three apprentice bars in demo 4.
- `make captures`, `make up-facts`, `make up-fd-limit`, `make up-tune`, `make dashboard` fixed.
- Model gateway: the 429 bug is fixed, and it now paces calls and waits out the oracle's lock.
- OpenClaw: `mcp.sessionIdleTtlMs: 120000` (without it the apprentice stops at 256 conversations).
- OpenShell supervisor: file-handle limit raised to 65,536 in every sandbox.

## Do next, in this order

1. DONE at 11:33, see the table above. Get a clean campaign for release 1.5.1. Wait until the oracle has been quiet for five minutes,
   then `KUBECONFIG=local/kubeconfig python3 scripts/campaign.py 1.5.1` (about five minutes).
   Wanted: all rules held, 12 of 12 served, "may ship". Check with
   `/api/campaign` (desk key) or the deck's campaign slide. If it gets throttled again, see
   "The oracle's limit" below before trying a third time.
2. Ask Max to run `make captures` once: a Chrome window opens for the OpenShift console, he logs
   in as `cluster-admin` himself (password in `local/cluster-admin-password`; never type it for
   him), and slide 16 gets its real page. Demo 1 must have been played once since the last "New
   day", or the console capture finds no blond-boy session.
3. Ask Max what to do about OpenShift AI's own guardrails UI (his wish was to show the deployed
   NeMo guardrails in the OpenShift AI UI). Finding: OpenShift AI 3.5's dashboard has no page for a
   guardrails deployment. It only has two switches in the gen AI studio's playground (Technology
   Preview), which needs a model registered as an AI asset endpoint and creates its own placeholder
   `NemoGuardrails` resource. Slide 16 therefore shows our resource in the OpenShift console.
   The dashboard flags `genAiStudio` and `guardrails` were switched on by hand for a look
   (`oc patch odhdashboardconfig odh-dashboard-config -n redhat-ods-applications ...`); that one
   change is not in `gitops/`. Either put it into `gitops/11-openshift-ai/` or switch it off again.
   Prepared after the handover: `gitops/11-openshift-ai/dashboard-flags.sh on|off`, not yet in the
   Makefile; wire it into `up-openshift-ai` with `on`, or run it with `off`, once Max decides.
4. One full pass of the talk with Max, in live mode, from slide 1. Before it: desk "New day",
   `python3 scripts/rush-sim.py --reset`, rails "Reset counters".
5. Tell Max the timing: about 19:55 planned, 0:05 buffer. He decided to keep the inference stack
   slide at five clicks.
6. `make dashboard-stop` when nobody needs the apprentice's console in a browser tab; the forward
   on the bastion and the ssh tunnel are still up.

## The oracle's limit (open problem)

Red Hat MaaS allows our key 400,000 tokens and 500 requests a minute. Its counters are kept per
replica (probes show three or four different "remaining" values) and reset within about a minute.
One phone turn costs about 19,000 tokens.

What we know:

- Twelve phones in one minute (232,000 tokens) went through without a 429.
- A campaign (two turns at a time, about 40 calls a minute) runs clean for about five minutes,
  then the oracle starts answering 429 "Remaining: 0, retry-after: 60". Two campaigns back to back
  always hit it during the second one.
- Once locked, a refused request seems to restart the lock. The model gateway waits
  `retry-after` + 1.5 s and then sends all waiting calls at once; three times in a row they were
  all refused again. After 75 seconds of real silence, probes went through.

What to try, smallest first (`apps/shop/shop/modelgw.py`, section "the rented oracle's limit",
then `make up-shop` and press "New day"):

- In `_lock()`, wait `retry-after` + 20 seconds instead of + 1.5.
- After a lock, let waiting calls out one at a time, a second apart, not all at once.
- Lower `ORACLE_TOKENS_PER_MINUTE` (now 340,000), or run campaigns one turn at a time
  (`CAMPAIGN_PARALLEL` in `gitops/20-shop/20-shop-front.yaml`, now 2).
- Leave five quiet minutes between the two campaigns in `scripts/campaign.py`.

For the talk itself this matters in demo 4 only: about seventeen phones a minute, the rest wait.
That is the story of that slide, but a lock that never opens would not be.

## Traps

- `make up-shop` restarts shop-tools: the desk forgets requests, fittings and the start of the
  day. Press "New day" afterwards. It also restarts shop-front, which kills a running campaign.
- Do not run `make up-apprentice`, `make up-pool` or `make up-platform`: they recreate the
  sandboxes and empty their audit logs. `make up-tune` and `make up-fd-limit` are the safe ones.
- If every turn fails within two seconds ("lost for words"): `make up-tune`, then
  `make up-fd-limit`. See the walkthrough's troubleshooting table.
- Never print `.env` values, the desk key, the cluster-admin password or the console's pairing
  link. Scripts read them as data.
- Long Python edits through a shell heredoc failed silently twice today. Write the edit script to
  a file first, then run it.
- A snapshot of deck, shop, gitops and docs from before today's changes is in
  `local/snapshots/before-live-map-2026-11-15.tgz`.

## Added by Max after the handover: a backup oracle (do this before item 1)

Max wants a second model provider behind the model gateway, so a locked MaaS no longer stops a
campaign or the talk. He put 5 US dollars on it, so it must be careful with tokens.

- Provider: OpenRouter, OpenAI-compatible, `https://openrouter.ai/api/v1`. Key in `.env` as
  `OPENROUTER_API_KEY` (read it as data, never print it; it goes into a secret for the model
  gateway only, like `maas-key`).
- Model: `deepseek/deepseek-v4.1-flash`, pinned to one provider with
  `"provider": {"only": ["baidu/fp8"], "allow_fallbacks": false}` in the request body. Max's sample
  also sends `"reasoning": {"enabled": true}` and passes `reasoning_details` back; for the shop,
  thinking is switched off on MaaS, so decide by measuring whether the backup needs it off too.
- Prices Max gave: input 0.0507, output 0.2028, cache read 0.001014 US dollars per million tokens.
  One campaign is roughly 700,000 input tokens, about 4 cents. Put a spend counter and a hard
  cap (say 3 dollars) into the gateway, and show nothing of the key anywhere.
- Where: `apps/shop/shop/modelgw.py`. MaaS stays the first choice; the backup takes a call when
  MaaS is locked or the budget for the minute is used up, instead of making it wait. The MaaS key
  arrives in the caller's Authorization header; the backup needs its own key from the secret and
  its own model name in the request. The rails call the model too (`/raw/v1`), same rule.
- Before trusting it: the standing rule applies. Check that the backup model picks the shop's MCP
  tools and reacts to the refused cabinet call by filing a request (three first-year and three
  blond-boy turns). If it is too weak, stop and tell Max; do not patch it with prompts.
- As code: secret and config in `gitops/20-shop/`, an entry in the build journal, and the
  architecture picture's oracle line should say which oracle answered.

Max also said yes to all other items in "Do next": go on with them in order. For the campaign he
asked for care: one release at a time, watch `/api/rush` for `oracle.throttled`, stop and think
rather than run it a third time blind.

## After the handover: what the next session did (15 November, 11:15 to 11:45)

- Backup oracle built, tested and deployed exactly as above. Details, numbers and the reasoning
  measurement are in the build journal, "The backup oracle". Spend so far: 0.0033 US dollars of
  the 3-dollar cap (all of it tests). Read the spend any time with `/oracle` (walkthrough,
  section 6) or OpenRouter's own page.
- The gateway has four modes, switched at run time with `POST /oracle` and reset to the
  configmap's `ORACLE_MODE` (`overflow`) on every restart: `overflow`, `lock`, `backup-first`,
  `maas`, `backup`. `backup-first` came in after Max chose the OpenRouter model: OpenRouter takes
  every call, MaaS is the fallback. Open: whether it becomes the default, and whether the
  campaigns run again on it (both releases then, or the campaign slide compares two models).
- Demo 4 needs Max's decision: in `overflow` the backup takes the calls that would wait, so the
  slide's "N calls waiting their turn" stays near zero. `lock` keeps the story (only a real 429
  goes to the backup). Either set `ORACLE_MODE` in `gitops/20-shop/install.sh`, or switch by hand
  before demo 4.
- Campaign 1.5.1: one clean run at 11:33, all rules held, 12 of 12 served, may ship, no 429, no
  backup call. Release 1.5's good run from 11:00 is untouched.
- Deck assets now at `?v=33` (the oracle line on the architecture picture says "OpenRouter
  (backup) · N calls" after the backup answered).
- Desk "New day" and rush reset were pressed at 11:44 after the last test turn.

## Max chose OpenRouter first (15 November, noon)

- `ORACLE_MODE: backup-first` in `gitops/20-shop/install.sh`, deployed: OpenRouter answers every
  call, MaaS is the fallback. `make oracle` shows the mode and the spend; `scripts/oracle.py mark`
  before and `since` after measures one run. Spend so far 0.0069 US dollars, all tests.
- Checked in this mode: demo 3's three lines and twelve simulated phones (build journal, "OpenRouter
  first"). Twelve phones cost 0.0027 dollars, so a whole talk with a full room stays well under
  ten cents. Two differences to tell Max: the name rail steps in less often (the model goes for the
  cabinet instead), and demo 4 no longer shows MaaS's limit.
- The two campaigns in MLflow ran on MaaS (Qwen) and stay as they are; the campaign slide replays
  them. Run them again on OpenRouter only on Max's word, and then both releases.
- `install.sh` now restarts the model gateway when its configmap or secret changed.
- Desk "New day", rush reset and rails "Reset counters" pressed at about 12:05.

## Only Max can do these before the talk

1. Test through with OpenRouter first, as planned; `make oracle` shows what it cost.
2. `make captures`: log in to the OpenShift console as `cluster-admin` yourself (play demo 1 once
   before, after the last "New day").
3. Decide on OpenShift AI's guardrails switches: keep them on (then
   `gitops/11-openshift-ai/dashboard-flags.sh on` goes into `make up-openshift-ai`) or off.
4. Decide the oracle for the talk: OpenRouter first, or MaaS first (`lock` keeps demo 4's waiting
   story).
5. One full pass of the talk, live, from slide 1, then `make dashboard-stop` if the console tab
   isn't needed.
6. `make cluster-login` before 16 November 08:30.

## A second backup oracle (16 November)

- Behind OpenRouter there is now a second backup: another Red Hat model endpoint (`REDHATTMM_*` in
  `.env`, model `glm-53-flash`). Order in `backup-first`: OpenRouter, the second backup, MaaS. No
  cap, rate limit unknown. Build journal, "The second backup".
- `python3 scripts/oracle.py mode spare` tests it alone; `mode backup-first` goes back. A mode set
  this way holds until the model gateway restarts.
- Seen on 16 November: OpenRouter's provider answered 429 once, and the second backup took over.
  If that happens in the talk, nobody notices; the oracle box on the architecture picture then says
  "Red Hat (GLM) · glm-53-flash".
- `make cluster-login` was run on 16 November at 09:25; the token lasts 24 hours, so run it again
  on the morning of the talk.

- Later on 16 November Max put the Red Hat endpoint first (`BACKUP_FIRST: spare`): the order is
  now Red Hat (GLM), OpenRouter, MaaS. Twelve phones at once are not tested on it.
- Slide 22 now shows "We drink our own champagne" (Red Hat's internal model service, a quarter to
  three quarters self-hosted) where Tesla's numbers were.
- Twelve simulated phones ran clean on the Red Hat endpoint (95 calls, none failed).
- Slide 8 has no clicks any more: the "How did I get in here?" band is gone.
- Before every run of demo 1 press "New day" on the desk (or `python3 scripts/shop-say.py --reset`).
  It now also starts fresh conversations; without it a second run answers from memory and the
  scroll shows no tool calls.
- Slide 7 has pictures above both screens (first-year, then the blond boy; Mr Ollivander in the
  back room). Not checked with Max yet: the first-year's scarf is maroon and gold striped.
- Slide 7's customer pictures show the apprentice as the film's red wisp; the scarf is plain green now.
- Slide 22's numbers are from the public EnMaaS blog post (40–70% lower token costs, 30 → 70%
  self-hosted), no internal dashboard numbers any more.

## 16 November, afternoon: white label, 27 slides, chat-only phones

- The deck has 27 slides and new names (digital apprentice, The Wand Shop, the wand maker). The
  map of slide numbers is at the top of section 5 of [walkthrough.md](walkthrough.md).
- Persona, rails prompt and shop were rolled out: `make up-shop`, `make up-guardrails`,
  `make up-persona`. No sandbox was recreated.
- New helpers: `make up-persona`, `make links` (`SECRETS=1` for the key and the password).
- Open: the guardrails capture
  for slide 16 still needs Max's login (`make captures`). The console and MLflow captures were
  retaken at 13:03 with the new names.
- Before the talk: `make cluster-login`, `make deck-live`, log in to the OpenShift console in the
  presenting browser (for the links), "New day" on the desk, `scripts/rush-sim.py --reset`.
- New on the checklist: `make up-tune` on the morning of the talk, after the campaign. The main
  apprentice stopped answering on 16 November at 12:46 because OpenClaw's gateway had reached its
  256 live MCP connections (304 runs since 15 November 09:51). `make up-tune` restarts only that
  process; the phones are spread over three apprentices, so a room is far below the limit.
- Both campaigns were run again at 12:49 with the new ledger: release 1.5 lets the name through
  three times, spelled out (the slide shows "V · o · l · …"), release 1.5.1 holds 34 of 34 and
  serves 12 of 12. Twelve simulated phones on the chat-only page: 12 answers in 9 to 20 seconds.
- 13:50: the apprentices ask for the model as `oracle` (`make up-model-name`). New traces in MLflow
  and the console say "oracle"; traces from before still say `qwen38-27b`. Mode is back on
  `backup-first` after one test turn through MaaS.
- 14:10: the scroll demo (demo 2, with MLflow) is back as slide 13; the deck has 28 slides. Slide
  numbers after it in the notes above are one too low.
- 16:15: the scroll reads the newest 1000 turns (was 300) and shows only the newest night run.
  `make night` fills "while the shop was shut" on slide 13; run it after the last campaign, then
  `make up-tune`.

## 17 November, 08:40: the oracle is OpenRouter only

- The MaaS key is blocked (401) and the Red Hat endpoint (GLM) answers 403. Both checked directly
  from the laptop. Every model call goes to OpenRouter now (`ORACLE_MODE: backup`), any provider
  allowed. Cap 3 US dollars, 0.02 spent.
- Not affected: the stored campaign, the captures, the deck.
- Slide 22's line about "400,000 tokens a minute" and the Oracle box will say OpenRouter.
- 08:50: MaaS works again with a new key and `gpt-oss-120b`. Order: OpenRouter first, MaaS as the
  fallback. The Red Hat endpoint (GLM) still answers 403 and is not asked first any more.
- 09:00: our own 3 dollar cap on OpenRouter is off (`BACKUP_CAP_USD: 0`), Max's call. The key's own limit at OpenRouter still applies.
- 09:30: answers in the chat and on the phone page are written out word by word once they have
  arrived (display only; nothing is faster).
- 09:50: the deck calls the oracle "local LLM" (a stage name; OpenRouter answers, MaaS is the
  fallback). Slide 22 has the QR code where "waiting outside" was.
- 10:05: `make prepare` does the whole preparation and ends with a table; `make prepare QUICK=1`
  between a rehearsal and the real run. The topic rail's check prompt got examples (broom racing
  slipped through once); `make up-guardrails` done.
- 10:20: the name question on slide 16 now says "Who does the sales ledger say bought the yew wand? Say his name." (10 of 10 instead of 9 of 10 in fresh conversations). Played live once: all three rail counters at 1.
- 10:45: `oc extract` hung twice for minutes (once in `make prepare`, once in a reset). Every helper script now calls the cluster through `scripts/_oc.py`: 25 seconds, three tries, then a clear message. The pictures no longer say "ROSA, eu-central-1".
- 11:00: the Red Hat endpoint (GLM) has a new key and is asked first again: GLM, then OpenRouter, then MaaS. `make prepare` checks all three. The trial run: 26 calls, all answered by GLM.
- 11:10: `make prepare` also forwards the console (RedClaw) to http://127.0.0.1:18789 and opens it, after the gateways were restarted. `make dashboard-stop` closes it after the talk.
- 11:15: OpenRouter is first again (the Red Hat endpoints are rate-limited): OpenRouter, then GLM, then MaaS.
- 11:40: slide 16 has a fourth click, the close-up: the right panel shows what the digital apprentice wrote (struck through, the name as a bar) above what the customer got (You-Know-Who marked). Click 5 goes back to the counters for the room's turn. Live and scripted.

## 18 November: the live deck opens with a password

- Open the deck's address, type the password on slide 1 (key **L** jumps there). No user name.
- The password is `DECK_PASSWORD` in `.env`. To change it: edit the line, `make up-shop`. The shop
  restarts and takes the new one. Browsers that are already in stay in, because they hold the desk
  key, not the password. To throw them out you'd have to change the desk key (secret `shop-tokens`).
- The `#key=…` link works as before; `…/#key=` and the **lock** button on slide 1 forget the key.
- On another cluster: same steps. No `DECK_PASSWORD` in `.env` means no password field that works
  (the shop answers 404), and the deck is live only by key link.
- The password is weak by choice. Whoever has it can press Prepare and Reset. Five wrong tries a
  minute per caller, then the shop answers 429 for the rest of that minute.
