# BentaBuddy

A local-AI order manager for Filipino bakeries and home food sellers. Turn Taglish customer messages into an owner-reviewed order, then track preparation, fulfillment, verified payments, and repeat customers.

**AI inference runs on the owner's computer.** Qwen3 4B reads the conversation and catalog through a loopback-only llama.cpp endpoint. No cloud AI key or service is used. Training a new model is not required.

## Run on this Mac

The dependencies, production build, portable runtime, and verified 2.5 GB model are already installed in this workspace.

```bash
cd BentaBuddy
./scripts/start.sh
```

Open **http://127.0.0.1:8000**. On first launch, create your local owner account with your bakery name, email, and a password of at least 10 characters. Future visits require login; the sidebar has a Log out button. This is one local bakery account, with no email verification or cloud account service. Keep the Terminal open; Ctrl+C stops the app and the model it launched. The model may take a little time to load. Settings shows model readiness; the runtime log is `data/local-ai.log`.

For a fresh Apple silicon checkout, install Node.js 22+ and Python 3.9+, then run:

```bash
./scripts/setup.sh
./scripts/start.sh
```

Setup needs internet to install dependencies and download the model. Subsequent startup, imports, inference, orders, and analytics work without internet. SQLite is at `data/bentabuddy.sqlite3`; back up the entire `data/` folder with the app stopped. No data is sent to analytics services.

### Phone demo

The Mac mini hosts both the app and AI. The phone is a browser client; it does not run the model. Connect both to the same trusted Wi-Fi or local hotspot and start explicitly with:

```bash
./scripts/start-phone.sh
```

Stop any existing BentaBuddy app process first (Ctrl+C in its Terminal), then run this command. It prints active local network URLs; open the matching `http://MAC_IP:8000` address on the phone and sign in with your existing bakery owner account. Leave the Facebook tunnel running. The address can change when switching networks. You can also find the Mac's Wi-Fi IP in System Settings → Wi-Fi → Details. A local network is required; an internet connection is not. macOS may ask to allow incoming connections. The dashboard and management API require the local owner login. The LAN demo uses HTTP, so use a trusted network and fictional data; do not use it as a public production deployment. Keep the AI port 11434 on loopback. Do not expose the full dashboard/API publicly.

### Optional Ollama runtime

The generic `qwen3:4b` tag resolves to a Thinking-only model and is unsuitable for this extraction configuration. Use the pinned Instruct tag below. If you already have Ollama installed, run `ollama pull qwen3:4b-instruct-2507-q4_K_M` while online, then:

```bash
BENTABUDDY_RUNTIME=ollama ./scripts/start.sh
```

For an alternate installed model set `BENTABUDDY_MODEL` as well. Do not run both runtimes on port 11434. The bundled setup script targets Apple silicon; other machines can use the Ollama option after installing the app dependencies and building the frontend.

## What is built

| Module | Behavior |
| --- | --- |
| Today | Due orders, recorded payments, remaining preparation, handoffs, and review queue |
| Inbox | Manual message imports, conversation follow-ups, local AI extraction, source excerpts, review/approval |
| Orders | Create/revise, date/status/search filters, CSV export, owner-entered payments, activity history |
| Preparation | Quantities in base units and fulfillment board, separated by due date |
| Customers | Separate customer records, order history, fulfilled-order counts |
| Analytics | Fulfilled order value, recorded payments, popular products and frequent customers by date range |
| Catalog | Prices, supported units, availability, and Taglish/product aliases |
| Settings | Actual local model status and Facebook setup information |

**Demo bakery** starts with 55 fictional orders, eight customers, six products, and a sample conversation. Switch to **My real orders** for your own records. The catalog is shared between the two workspaces. AI drafts are never faked or preapproved.

Owner approval is required before a message affects production. The save confirmation and approved Inbox message include **View in Preparation**, which opens the order’s scheduled date and highlights its card. Preparation remembers the selected date and provides Today, Tomorrow, upcoming-date, and overdue shortcuts. Quantity conversions are shown during review before approval. Dozens convert to 12 pieces. Revisions update the same order and reject stale versions; item changes return the order to the queue. Prices are copied into approved order lines; later catalog edits do not alter saved orders, while explicitly revising an order uses current prices. Delivery and pickup follow different transitions. Fulfillment does not imply payment. Only an owner-recorded payment affects the payment balance. Canceled orders retain their payment history for refund review.

## Facebook Page integration

Follow [docs/FACEBOOK_SETUP.md](docs/FACEBOOK_SETUP.md) for the local credential helper and webhook-only HTTPS tunnel.

The signed webhook receiver is implemented; **a real Page is not connected yet**. Use Inbox → Import message for a reliable demo until your own Meta app/Page access is ready. The importer is labeled manual and does not impersonate Messenger.

Copy `.env.example` to `.env` and fill in your own values. Start scripts load it server-side. In your Meta app configure the Messenger Page webhook callback as your public HTTPS relay's `/api/facebook/webhook`, verify using `META_VERIFY_TOKEN`, and subscribe your authorized Page to message events. Live availability depends on your Meta app permissions, review/access status, and Page subscription; merely setting secrets does not establish that access.

The relay must forward **only** `/api/facebook/webhook` to this machine. Preserve raw POST bytes and `X-Hub-Signature-256` so signature verification succeeds. Keep management APIs private. Receiver verifies signatures, filters the configured Page, ignores message echoes, deduplicates message IDs, stores the text locally, and queues local inference. It does not send customer replies or retrieve historical messages. Optional customer names/photos use a separate Meta profile lookup: run `.venv/bin/python -B scripts/configure-facebook-profile.py`, enter a fresh Page access token privately, restart the app, and send a new message. Photos are cached locally; denied access retains the placeholder. See [Facebook setup](docs/FACEBOOK_SETUP.md). Without live Facebook access, do not claim the demo is connected.

Internet is necessary for receiving new Facebook events. When it drops, previously received conversations, local AI extraction, imported text, and bakery operations continue locally.

## Demo flow (about one minute)

1. Open Demo bakery → Inbox → the sample Mika conversation. Click local AI extraction; let the real model finish.
2. Show the original “2 dozen” followed by “gawin na lang 3 dozen, 9am.” Review the expected **36 pieces**, tomorrow relative to the message timestamp, pickup at 9 AM. Correct any model error openly before approval.
3. Approve and open Preparation. Select the requested date to show the new quantity.
4. Add a follow-up “Gawin na lang 4 dozen, same pickup time,” extract again, and approve the revision. Show **48 pieces on the same order**.
5. Mark preparing → ready → fulfilled and record a payment separately. Show customers/analytics.

For the offline portion, disconnect upstream internet while keeping the Mac/phone local network connected. Re-run extraction on an imported message. An actual successful offline extraction is the evidence of local AI; a dashboard alone is insufficient. Record latency from your real run rather than claiming benchmark numbers.

## Development and validation

```bash
npm test
npm run build
# Optional frontend development, alongside the backend:
npm run dev
```

React + TypeScript + Vite frontend; FastAPI backend; SQLite; Qwen3 4B quantized GGUF; llama.cpp or Ollama local inference. Single-process AI queue with persisted job status. Restart marks interrupted jobs failed and allows retry; no cloud fallback.

Verified during implementation: production compilation, 32 business workflow/auth/parser/relay/profile tests using FastAPI's in-process TestClient, model checksum, and dependency lock consistency. Tests cover units, stale revisions, approval, local-only model transport, source evidence, fulfillment, payments/idempotency, cancellations, persistence recovery, and signed webhook deduplication, login/logout, hashed credentials, session expiry, and cross-origin mutation rejection. **Model calls in the automated suite are mocked.** Three additional real local CPU inference checks passed: the corrected 36-piece order at 09:00 tomorrow, a 48-piece revision preserving its schedule, and inquiry classification. See [docs/AI_VALIDATION.md](docs/AI_VALIDATION.md) for actual timings and reproduction. This session cannot reach local server ports or use a browser, so production HTTP extraction after restart, phone behavior, and visual browser QA remain unverified. Run `.venv/bin/python -B scripts/check-ai.py` from a second Terminal after starting the app to exercise the real HTTP model transport without changing bakery records.

Current scope limits: single owner account, no password-reset email or multi-shop separation, no refund ledger, no partial preparation quantities, no inventory or ingredient forecasting, no automatic Messenger replies, no historical message sync. Relative dates and Taglish interpretation require model evaluation. Long conversations use the latest 25 messages; AI outputs still require human review. Older overdue orders are available using Orders date filters and the preparation date picker rather than included in today's preparation total.

See [BUILD_PLAN.md](BUILD_PLAN.md) for event criteria and [docs/DISCLOSURES.md](docs/DISCLOSURES.md) for model and tool disclosures. Target repository: https://github.com/GABlane/BentaBuddy. To publish from your own Terminal, run `./scripts/publish-github.sh`; it signs in through GitHub CLI if needed, adds the remote, commits as GABlane without a co-author trailer, and pushes to main. The social post and final hackathon submission remain the team’s responsibility; no event submission has been performed.

Team live validation: the owner confirmed Meta webhook verification, receipt of a real Messenger message, local extraction of 20 cheese pandesal for October 10 at 10 AM, and a follow-up correction to 30 pieces at noon. Optional profile lookups remain unverified with live Meta credentials.


### Separate purchases in one conversation

Extraction uses messages since the last approval and the active approved order as context for revisions. Completed/canceled order items are excluded. If no new messages exist, extraction stops instead of proposing an old order again. The full conversation remains visible.

For a separate purchase while a previous order is still open (or to separate multiple unapproved requests), click **Start new order here** beneath the first message of the new purchase. Confirm the change, then review the new proposal. The chosen message and later messages form the request; earlier confirmed orders remain saved and customer history is preserved. This replaces pending drafts and rejects stale approvals. Existing saved conversations recover their last approved boundary from approval jobs where available.


Phone connection troubleshooting: enter `http://` explicitly, use port `8000`, and ensure the app was started with `scripts/start-phone.sh`. If prompted by macOS, allow incoming connections for the local Python app. Guest/venue Wi-Fi may isolate devices; use a trusted shared network or hotspot that permits device-to-device access. The Cloudflare URL forwards only Facebook webhooks and cannot open the dashboard. For an offline phone demonstration, keep local Wi-Fi connected while disconnecting upstream internet. Starting normally with `./scripts/start.sh` returns to loopback access unless `.env` explicitly sets another host. An explicit `BENTABUDDY_HOST` command override takes precedence over `.env`.
