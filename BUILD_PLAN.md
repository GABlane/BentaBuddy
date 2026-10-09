# BentaBuddy — local AI bakery order manager

## Product decision

Replace the earlier offline study concept with a responsive order-management website for a Filipino bakery or home-based food seller. Internet is allowed for Facebook Page messaging. Meaningful AI inference runs on the owner's M4 Mac mini (16 GB unified memory), using a downloaded model; no cloud AI provider is required. Google Sheets is optional future export, not the primary product or database.

Product promise: turn messy customer conversations into reviewed orders, then help the owner know what to prepare, what to fulfill, and what customers buy most often.

Status: eight modules and local owner login implemented. Production build and 32 automated workflow/auth/parser/relay/profile tests pass. The owner confirmed real Facebook delivery, customer names/photos, Taglish quantity/time corrections, and offline operation. Request scoping now separates reviewed messages from new requests, with an explicit new-purchase boundary. Remaining gates: expanded Taglish accuracy checks, phone/browser verification, approved-order revision and complete fulfillment demo, current repository publication, and hackathon materials. See docs/AI_VALIDATION.md for model test scope.

## Event constraints

Source: AppBuildersPH-Hackathon-2026-Participant-Briefing.pdf, read in full (29 pages).

- Official build window: October 9, 2026, 2:30 PM to October 10, 10:00 AM Manila. Submission and code freeze at 10 AM; no extensions or post-deadline commits. The original 19.5-hour window is shrinking; prioritize the complete core workflow over module count.
- Meaningful local inference, substantial event-time development, working demonstration, and model/tool disclosures are required. Existing pretrained models and AI-assisted development are allowed; training is not required.
- Public GitHub repository with reproduction instructions; project/team details; demo video ideally about one minute; required X/LinkedIn video post tagging Devin/Cognition and using #AppBuildersPH; local/internet boundaries and existing-code/asset/AI-tool disclosures.
- Submission through Cerebral Valley occurs once; edits/resubmission are not allowed. Prepare and verify materials before asking the user to publish or submit.
- Five-minute pitch including live demo, then three-minute Q&A. Finalist representatives must attend Cyberzone, SM Makati. Noon arrival, 12:15 PM AV checks. Power/HDMI/USB-C are promised; a spare monitor is not. Arrange display/input for the Mac mini.
- Weights: usefulness 25%, local AI 25%, execution 20%, innovation 15%, UX/demo 15%.
- Only official listed participants compete; outside human help is prohibited. Disclose Codex and agent assistance. Do not publish real customer information, secrets, or the briefing without appropriate authorization.

## Modules and priority

### 1. Today dashboard — required

- Confirmed orders due today, orders needing review, overdue fulfillment, and upcoming pickup/delivery times.
- Quantities to prepare by product, variant, and due time, with drill-down to contributing order lines.
- Remaining preparation totals exclude canceled items and account for already prepared quantities without silently hiding overdue work.
- Outstanding payment balance separate from fulfilled sales. Money displayed in PHP with integer-centavo storage and code calculations.
- Counts use defined date/status filters; no LLM-generated metrics.

### 2. Inbox and AI review — required; product's central AI feature

- Facebook Page messages when access is available; clearly labeled paste/import input as fallback.
- Side-by-side source conversation and proposed order.
- Local AI extracts product, quantity/unit, variant, requested fulfillment date/time, pickup/delivery, stated contact/address, special instructions, and changes/cancellations.
- Recognize inquiry vs proposed purchase; ask about ambiguity rather than turn every message into an order.
- Catalog matching uses known products/aliases. Unknown product, relative date ambiguity, unsupported modification, or missing quantity/time stays flagged.
- Highlight source message IDs/excerpts and changes. Never invent missing details.
- Owner can correct, approve, or dismiss. New messages cannot silently overwrite an approved order or change the production queue; revisions need review.
- Draft customer clarification text may be copied manually. Automatic customer replies are outside MVP.

### 3. Orders — required

- Search/filter by order number, due date, customer, fulfillment status, and payment state.
- Order lines, authoritative catalog prices, totals, special instructions, source conversation, and revision history.
- Order state: draft, confirmed, canceled. Fulfillment and payments are tracked independently.
- Status changes validate allowed transitions and keep an audit record. Confirming an order does not certify payment or delivery.

### 4. Preparation and fulfillment board — required

- Production list grouped by product/variant and due time, with exact order links.
- Fulfillment state: queued -> preparing -> ready -> out for delivery -> fulfilled; pickup orders go ready -> fulfilled. Record canceled/failed attempts separately where needed.
- Staff explicitly marks preparation/readiness and fulfillment timestamps. No GPS, courier API, route planning, or automatic proof-of-delivery inference.
- Special instructions visible on order-level work items; do not automatically assume the bakery can safely meet a dietary request.
- Payment state never changes solely because fulfillment changed.

### 5. Customers — basic MVP

- Use Facebook Page-scoped sender ID plus Page ID as the identity key when available; use explicit local IDs for manually imported customers.
- Name/alias, customer-confirmed contact details, order history, last order, and fulfilled-order count.
- Never merge customers just because names are similar. Manual linking only.
- Frequent-customer list is a deterministic aggregate, not an AI prediction.

### 6. Analytics — small MVP

- Date-range controls with Asia/Manila as the shop timezone.
- Most ordered products by quantity AND by distinct order count; normalize catalog units (e.g. dozen -> 12 pieces) before summing; never combine incompatible units or variants blindly.
- Frequent customers ranked by fulfilled-order count; exclude canceled orders and demo records from real reports.
- Fulfilled order value, payments received, and outstanding balance shown separately. Do not call all confirmed bookings collected revenue or profit.
- For the demo, provide product ranking, frequent customers, and a simple daily fulfilled-sales chart only. No AI forecasting, profit reporting without cost data, or model-generated arithmetic.
- Explain metric scope: order-demand views use due date for confirmed active orders; fulfilled-sales/customer views use fulfilled timestamp; payments use payment timestamp. Labels must make this distinction clear.

### 7. Catalog/settings — minimal required configuration

- Small editable catalog: product name, aliases, variant, base unit, allowed selling units/conversions, and price.
- Shop timezone, hours/cutoff as reference information, local model availability, and connection state.
- Keep credentials server-side and outside the public repository.
- Roles, ingredient inventory, recipes, supplier management, multi-shop accounts, courier integrations, forecasting, and social marketing are later work.

## Architecture

React + TypeScript + Vite interface; Python FastAPI backend; SQLite persistent source of truth; local Qwen3 4B language model served by the portable llama.cpp runtime (Ollama is also supported; benchmark still required). FastAPI serves built frontend and API from one origin. No embeddings pipeline required for a small catalog and bounded conversation history.

Flow: Facebook Page -> authorized Messenger API/webhook -> local persisted messages -> local AI proposal -> owner approval -> order records -> preparation board/analytics.

Meta requires an authorized Page/app/token and appropriate permissions/access. General-customer access may require Advanced Access/App Review; do not assume readiness before checking the actual app. Incoming webhooks need a public HTTPS endpoint; a narrowly routed tunnel can forward to the local webhook. The AI model and management interface should not be publicly exposed by that tunnel. Verify webhook authenticity, store messages before acknowledging, deduplicate delivery IDs, and process inference asynchronously.

Historical conversation import is a separate permission-dependent feature, not a promise that all Page inbox history is accessible. Start with new text-message events. Photos, audio, comments, personal-profile inboxes, and payment-proof screenshots are outside MVP.

Internet is required for Facebook ingestion and any optional external export. Local review, preparation, analytics, and saved-message inference remain available without internet. Mac must be running for local inference; a phone is a browser client over LAN, not an independent AI host. Facebook already holds the messages, so privacy claim is specifically no extra cloud AI inference, not that data never enters the cloud.

Default application binds locally. Optional phone access can be explicitly enabled on a trusted LAN; a local owner account and expiring server-side sessions protect the management API. This remains a single-owner prototype. Keep the inference runtime on loopback. Use production assets bundled locally; no cloud inference fallback.

## Data design and AI boundary

Core entities: shop, products/variants/unit conversions, customers, conversations, messages, AI proposals, orders, order items, revisions, fulfillment events, payments, and jobs. Persist processing states and recover interrupted jobs. Single model worker for the demo.

AI generates bounded JSON matching a schema, including action (inquiry/new order/change/cancel/needs clarification), known product IDs, extracted fields, source references, and unresolved questions. Backend validates IDs, quantities, units, source excerpts, dates, and schema; rejects unsupported references and retries malformed output once.

Use message timestamps and Asia/Manila context for relative dates, show exact resolved dates for review, and ask when interpretation is ambiguous. Retain enough conversation and current approved-order context to understand a correction. Key extraction to conversation revision; stale model output cannot overwrite a newer draft/approved revision.

Only backend transaction code writes confirmed orders and inventory-independent preparation quantities. Catalog pricing, order arithmetic, date aggregation, and analytics use code. A customer's 'paid na' is an unverified claim; owner-entered payment record is separate. Proposed cancellations require review and must remove confirmed production quantities exactly once after acceptance.

Audit lifecycle: raw message -> proposal -> corrections -> approval -> order revision -> fulfillment/payment events. Exactly-once business effect is achieved with idempotency keys and database transactions, not an assumption of exactly-once webhook delivery.

## Build sequence and gates

1. Prove inference and message access first. Test ten original Taglish conversations against a small catalog, covering revisions, units, inquiries, cancellation, and missing fields. Check Page/app setup immediately with a 45–60 minute diagnostic timebox. If unavailable, keep clearly labeled import fallback and describe live integration status honestly.
2. Build the core slice: message/import -> local extraction -> review -> confirmed order -> preparation total -> saved restart. Use this gate before separate analytics pages.
3. Add fulfillment transitions and today dashboard. Verify confirmed changes and cancellation recompute the work list. Add manual payment records only if time permits; otherwise payment state remains explicitly unknown/untracked.
4. Add basic customers and three deterministic analytics views. Reuse the order data rather than build a separate reporting system.
5. Polish responsive navigation, empty/error/loading states, startup instructions, and demo. Reserve at least two hours before submission for video, disclosures, public repository checks, and single-submission review. No stretch work that consumes this reserve.

Essential visible navigation: Today, Inbox, Orders, Preparation, Customers, Analytics. Catalog can be a small settings screen. Separate modules share one database and one order workflow; they are not separate products.

## Meaningful checks

- Ten labeled Taglish conversations: extraction correctness, source support, unit conversion, inquiry handling, and clarification for unknowns. Model multilingual claims are not proof of Taglish quality.
- Same customer changes two dozen to three dozen and changes pickup time: reviewable revision updates exactly one order; quantity becomes 36 base pieces after approval.
- Two different customers with the same name stay distinct.
- Duplicate webhook/retry creates no duplicate message/business effect; stale generation cannot replace newer changes.
- Cancellation and canceled line items leave production totals correctly after review.
- Fulfillment and payment do not change one another implicitly.
- Known fixture totals match dashboard and analytic results for dates/statuses/units, including midnight boundaries.
- Missing model/API access, invalid proposal, interrupted job, and backend restart fail visibly and preserve saved work.
- With internet disconnected, reprocess already available messages using local AI, approve orders, inspect preparation and analytics, and save progress. New Facebook messages cannot arrive while disconnected.

## Demo and disclosure

Five-minute pitch: brief Filipino bakery problem, live conversation -> proposal -> owner approval -> production board, quantity/time change, and product/customer analytics. Show local inference and distinguish actual live Page integration from imported fixtures. Include a short disconnected reprocessing segment if useful to demonstrate locality. Use original synthetic data and label seeded historical orders as demo data; no fabricated latency/usage claims.

Required roughly one-minute video: customer message, highlighted local AI order, owner approval, preparation list, and quick ranking/customer view. If edited for time, identify cuts rather than imply measured live speed.

Repository must disclose exact model/runtime, APIs, frameworks, code/assets, Codex/agents, internet requirements, limitations, and reproduction steps. No automatic publishing, external customer replies, or final hackathon submission without explicit user authorization.

## Pending inputs

- Facebook Page/app access and profile lookup confirmed by the owner; public customer access still depends on Meta approval.
- Small bakery catalog, example prices/units, and pickup/delivery workflow.
- Official team names, demo display, representative user feedback, and current time remaining.

## References checked during planning

- Participant briefing: local file in workspace, full 29-page review.
- Meta Messenger requirements: https://www.postman.com/meta/messenger-platform-api/collection/iyp204x/messenger-platform-api
- Meta Conversations API/access: https://www.postman.com/meta/messenger-platform-api/folder/22794852-255610cd-47f5-4f4d-b3fa-71aec360be9a
- Meta webhook sample: https://github.com/fbsamples/messenger-platform-samples/blob/main/node/README.md
- Local model candidate: https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M
- Structured outputs: https://docs.ollama.com/capabilities/structured-outputs

## Local owner login implemented

First launch creates a single local bakery owner account. Later visits require email/password login. Credentials use salted PBKDF2-SHA256 hashes; random session cookies are HttpOnly and SameSite Strict, backed by hashed session identifiers in SQLite and a 24-hour expiry. Logout revokes the session. Management APIs require authentication; Meta signature verification still protects the public webhook. Sign-in UI uses a bundled generated bakery photo with CSS blur and a centered cream card. No cloud identity service or email recovery is used.
