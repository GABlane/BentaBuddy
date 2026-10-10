# BentaBuddy

**Your Facebook Page business buddy, powered by local AI.**

BentaBuddy turns customer conversations into owner-reviewed orders and bookings, then helps Filipino small businesses track the work through completion. It supports bakeries and food sellers, gadget shops, staycation hosts, and general product or service businesses.

The web app, database, and AI run on the owner's computer. A phone opens the responsive website over the same local network. **No cloud AI API is used; the phone does not run the model.**

For submission text and video narration, see [SUBMISSION.md](SUBMISSION.md). See [disclosures](docs/DISCLOSURES.md) and [validation evidence](docs/AI_VALIDATION.md).

## Why it is needed

For sellers who take orders through Facebook Pages, a conversation is also an informal order form. Customers use Taglish, change quantities, move pickup times, and add details across several messages. The owner must reconstruct the latest request while also preparing goods or serving customers.

BentaBuddy is designed to reduce repeated copying, missed corrections, and scattered records. It connects the conversation to what the owner needs to prepare, pack, deliver, or reserve. Local inference avoids sending conversations to an additional cloud AI provider and lets the owner keep working with saved messages when internet access drops. These are product goals; the prototype does not claim measured business savings or error-reduction rates.

## How it works

1. Receive new text messages from an authorized Facebook Page, or paste a conversation into Inbox.
2. Local AI reads the unreviewed request against the active business catalog and applies stated corrections.
3. Review a structured draft, supporting message excerpts, and clarification questions.
4. The owner edits and approves before an order or booking affects the workflow.
5. Track preparation, dispatch, guest arrival, or service progress; record payments separately.
6. View customer history, popular offerings, recorded payments, and fulfilled order value.

Example: “2 dozen cheese pandesal bukas, pickup 8am” followed by “gawin na lang 3 dozen, 9am” should become a draft for **36 pieces at 9am tomorrow**, relative to the message timestamp. The owner checks the actual result before approval.

## Tech stack

| Layer | Technology | Role |
| --- | --- | --- |
| Frontend | React 19, TypeScript 5.7, Vite 6 | Responsive website and production build |
| UI | CSS, Lucide icons, locally bundled Archivo font | Business themes and interface |
| Backend | Python, FastAPI, Pydantic, Uvicorn | API, validation, workflows, frontend serving |
| Storage | SQLite | Local catalogs, conversations, customers, jobs, orders, payments, events |
| AI | Qwen3-4B-Instruct-2507, Q4_K_M GGUF | Language interpretation and structured drafts |
| Inference runtime | llama.cpp; optional Ollama | Model execution on the owner's computer |
| Messaging | Meta Messenger webhooks, optional User Profile API, HTTPX | New Page text messages and permitted names/photos |
| Webhook transport | cloudflared / Cloudflare Quick Tunnel | HTTPS to a webhook-only local relay |
| Validation | Python unittest, FastAPI TestClient, model smoke scripts, TypeScript/Vite build | Workflow and inference checks |

Exact dependency versions are in `package-lock.json` and `requirements.lock.txt`.

## What AI we use

The default is **Qwen3-4B-Instruct-2507**, a pretrained 4-billion-parameter instruction model in **Q4_K_M quantized GGUF** format. The configured alias is `qwen3:4b-instruct-2507-q4_K_M`. llama.cpp serves it at `http://127.0.0.1:11434`. Startup disables thinking output and enables Apple silicon GPU offload. The development/demo host is an M4 Mac mini with 16 GB unified memory.

We did **not** train or fine-tune the model. Our application supplies task-specific instructions, up to 25 messages from the current unreviewed request, message dates, the active catalog, and relevant approved-order context. It requests schema-constrained JSON for the action, items, schedule, fulfillment details, notes, questions, source excerpts, and booking details. There is no embeddings/vector-database pipeline.

The model interprets language. Application code validates catalog IDs, units, quantities, dates, source quotations, and workflow transitions. Code calculates prices, dozen conversions, nights, booking conflicts, and analytics. Explicit separate purchases alongside open orders require an owner-selected boundary. Repeated model item lines require quantity clarification rather than increasing the total. Invalid or incomplete output fails visibly. **Human review remains required; there is no cloud inference fallback.**

## Business workflows and modules

| Business | Details | Workflow |
| --- | --- | --- |
| Bakery / food | Quantities, pickup/delivery, packaging | Preparation, ready, handoff, completion |
| Gadgets | Devices/accessories, model/color/variant | Packing, dispatch, handoff |
| Staycation | Individual units, dates, guests, nightly rates | Pending, confirmed, checked in, completed |
| General | Products/services, schedule, service location | Scheduled work and fulfillment |

Settings changes the business name/type, visual theme, labels, and catalog context. Each type has an editable catalog with example prices; switching back restores edits. Existing records and the connected Page remain saved. This does not create independent shop accounts or switch Facebook credentials.

The app includes **Today, Inbox, Orders, a business-specific fulfillment board, Customers/Guests, Analytics, Catalog, and Settings**. Orders support revisions, filters, CSV export, activity history, and manual payment recording. Customer claims are not verified payments; fulfillment and payment are separate. Saved lines retain approved prices; explicit revisions use current catalog prices. Stale proposals/revisions are rejected.

Staycation bookings include check-in/out, guests, and calculated nights. Each accommodation catalog entry represents one bookable unit. Pending requests do not hold dates. Confirmed-booking overlaps are checked transactionally; cancellation/completion releases dates. Checkout-day arrivals are allowed. Capacity pools and guest-limit enforcement are outside scope.

## Offline and internet boundaries

| Operation | Connectivity |
| --- | --- |
| Initial dependency/model download | Internet required |
| New Facebook messages, fresh profile lookups, public tunnel | Internet required |
| Saved messages and manual text imports | Offline |
| Local extraction, review, orders/bookings, work boards, payments, analytics | Offline after setup |
| Phone browser access | Local connection to the running Mac; internet not required |

Meta already processes Messenger conversations, and Cloudflare transports webhook traffic online. The privacy benefit is **no additional cloud AI inference**, not that messages never enter the cloud. New Messenger messages do not arrive offline. Historical inbox retrieval is not implemented.

## Run locally

**First time? Follow [the step-by-step setup guide](docs/SETUP.md)** for prerequisites, cloning, installation, your first AI extraction, phone access, Facebook, offline demonstration, and troubleshooting. The commands below are the quick start.

For a fresh Apple silicon checkout, install Node.js 22+ and Python 3.9+, then run from the repository root:

```bash
./scripts/setup.sh
./scripts/start.sh
```

If dependencies, weights, and the frontend build are already installed, only `./scripts/start.sh` is needed. Open **http://127.0.0.1:8000**. Keep the Terminal open; Ctrl+C stops the app and any model it launched. Settings shows model readiness; logs are at `data/local-ai.log`.

There is **no sign-in** in the current single-owner prototype. SQLite is at `data/bentabuddy.sqlite3`; back up the entire `data/` folder with the app stopped. Local data and credentials remain outside source control.

### Phone access

Stop the existing app, connect the Mac and phone to the same trusted Wi-Fi/hotspot, and run:

```bash
./scripts/start-phone.sh
```

Open the printed `http://MAC_IP:8000` URL on the phone. Allow incoming connections if macOS asks. The Mac must remain running. Guest networks may isolate devices, and changing networks can change the IP. Anyone on the local network can use the app in phone mode; use a trusted network and fictional demo data. The Cloudflare URL cannot open the dashboard. Keep model port 11434 on loopback.

### Optional Ollama

With Ollama installed, download `qwen3:4b-instruct-2507-q4_K_M` while online, then run:

```bash
BENTABUDDY_RUNTIME=ollama ./scripts/start.sh
```

Do not run both runtimes on port 11434. Use the pinned Instruct variant; the generic tag was unsuitable in the original tests. The bundled setup targets Apple silicon; other platforms need an appropriate local runtime and app dependencies.

## Facebook integration and request boundaries

Follow [Facebook setup](docs/FACEBOOK_SETUP.md) with your own authorized Page/app, permissions, secrets, and webhook subscription. The owner confirmed live receipt, profile display, corrections, and offline operation during development. Public-customer access remains dependent on Meta permissions and approval; eligible-account testing does not establish public access.

In a second Terminal, run `./scripts/start-facebook.sh`. Use the printed temporary HTTPS address plus `/api/facebook/webhook` as the Meta callback. Restarting the Quick Tunnel can change that address. Keep both app and tunnel running for live receipt. Only the webhook route is forwarded; the dashboard and model stay outside the public relay. The receiver verifies signatures, filters the configured Page, ignores echoes, deduplicates messages, stores text, and queues local inference. It sends no automatic replies.

Extraction uses messages since the last approval and the active order as revision context. Closed orders are excluded. For a separate purchase while an order is open, select **Start new order here** on its first message; earlier orders and customer history stay saved.

## Demo and sample records

Show a conversation/correction, real local extraction and evidence, owner approval, scheduled work, and customer/analytics views. Then disconnect upstream internet while keeping the local network connected, paste a fresh request, and demonstrate real extraction and saving. A dashboard alone does not demonstrate offline AI. Label fictional records and time-compressed video sections. See [SUBMISSION.md](SUBMISSION.md) for narration.

Fresh installations seed catalogs without fictional activity. Optional `.venv/bin/python -B scripts/seed-demo-messages.py` adds labeled sample conversations for all four business types; `--remove` removes those samples while keeping orders approved from them. `.venv/bin/python -B scripts/clear-demo.py` removes legacy demo activity. Both helpers back up data first. Requested sample orders are fictional records, not actual sales.

## Development and validation

```bash
npm test
npm run build
npm run dev
# Actual inference against the running local model, using temporary test data:
.venv/bin/python -B scripts/check-ai.py
.venv/bin/python -B scripts/check-business-ai.py
```

As of October 10, 2026, **52 automated tests and the production build pass**. Automated model responses are mocked. Separate real local-model checks passed core order scenarios and four business-theme scenarios using CPU CLI inference and temporary databases. Those checks do not verify the running HTTP server/browser or establish general model accuracy. Owner-confirmed live demonstrations are separate evidence. See [AI validation](docs/AI_VALIDATION.md) for failures, fixes, timings, CLI options, and reproduction.

## Current scope and disclosures

No sign-in or multi-shop isolation, automatic replies, social publishing, comment moderation, historical inbox sync, message image/audio processing, payment verification/collection, courier integration, inventory/ingredient forecasting, or AI sales predictions. AI outputs require owner review.

Codex assisted development; it is not the product's inference provider. See [model/tool/asset disclosures](docs/DISCLOSURES.md). [BUILD_PLAN.md](BUILD_PLAN.md) records planning/event notes; this README describes the current implementation.

Repository: [GABlane/BentaBuddy](https://github.com/GABlane/BentaBuddy). The team handles the final video, social post, and hackathon submission; this documentation update does not publish or submit them.
