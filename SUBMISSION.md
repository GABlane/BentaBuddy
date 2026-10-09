# BentaBuddy — Submission and video brief

## One sentence

**BentaBuddy turns Facebook Page conversations into organized, owner-reviewed orders and bookings using AI running on the business owner's own computer.**

Tagline: **Usap to order. Less hassle, ka-negosyo.**

## What the project is for

BentaBuddy is a responsive business-management website for Filipino sellers and hosts receiving customer requests through Facebook Pages. It connects the inbox to a structured order or reservation, then to scheduled preparation, dispatch, guest arrival, or service work. Customer history and analytics come from those saved records.

The prototype supports **bakeries/food sellers, gadget shops, staycation hosts, and general product/service businesses**, with editable catalogs and business-specific themes. It is a Page operations assistant; it does not publish posts, run ads, or moderate comments.

## Why it is needed

A customer conversation is rarely a complete order form. Customers use Taglish, change quantities and pickup times, add an address later, or modify booking dates. Owners must reconstruct the latest request while also running the business. Copying everything into notebooks or spreadsheets adds another manual step and separates the chat from fulfillment.

BentaBuddy is designed to reduce that repeated translation and make the next task clear. Local AI matters because an internet outage should not prevent the owner from analyzing saved messages or managing today's work. It also avoids sending conversations to another cloud AI provider. We do not claim measured time savings, commercial adoption, or perfect extraction accuracy.

## AI we use

- **Model:** pretrained Qwen3-4B-Instruct-2507, 4 billion parameters, Q4_K_M quantized GGUF.
- **Alias:** `qwen3:4b-instruct-2507-q4_K_M`.
- **Runtime:** llama.cpp on the owner's computer; optional Ollama support.
- **Our work:** task-specific prompts, catalog/message context, schema-constrained JSON, validation, and owner-reviewed workflows. No training or fine-tuning claimed.
- **AI responsibilities:** interpret Filipino/Taglish requests, apply corrections, extract offerings/quantities/schedules/details, distinguish inquiries and changes, suggest booking details, and ask about missing information.
- **Code responsibilities:** prices, unit conversions, nightly totals, booking-overlap checks, persistence, workflow transitions, and analytics.

The owner reviews every proposal. The AI does not verify payments or independently confirm room availability. There is no OpenAI/Google/cloud AI inference call or cloud fallback. Codex assisted development, which is disclosed separately.

## Tech stack

| Component | Technologies |
| --- | --- |
| Frontend | React 19, TypeScript 5.7, Vite 6 |
| UI | CSS themes, Lucide icons, locally bundled Archivo font |
| Backend | Python, FastAPI, Pydantic, Uvicorn, HTTPX |
| Database | Local SQLite |
| Inference | Qwen3 4B Instruct GGUF through llama.cpp; optional Ollama |
| Messaging | Meta Messenger webhooks and optional customer profile lookup |
| Webhook connection | cloudflared / Cloudflare Quick Tunnel to a webhook-only relay |
| Validation | unittest, FastAPI TestClient, actual-model smoke scripts, TypeScript/Vite build |

Development/demo host: **M4 Mac mini with 16 GB unified memory**. A phone opens the website on the same local network; AI remains on the Mac.

## How the demo works

1. Show a real authorized Page message or a clearly labeled manual/sample import.
2. Run actual local extraction and show the draft beside its source messages.
3. Review, edit if needed, and approve.
4. Show the order/booking on the correct date in the business workflow.
5. Briefly show customer history and analytics.
6. Disconnect upstream internet while keeping the local network connected. Paste a fresh message and demonstrate real local extraction and saving.

Example: “2 dozen cheese pandesal bukas, pickup 8am” followed by “gawin na lang 3 dozen, 9am” should produce 36 pieces at 9am tomorrow, relative to the message date. Check the actual generation before approval. Separate purchases within an existing chat use **Start new order here** to preserve earlier open orders.

A staycation example can show a studio booking for November 20–22 and two guests: two nights, initially pending. Backend overlap validation runs when the owner confirms. Each accommodation entry represents one bookable unit.

## Offline boundary

**Works offline after setup:** saved conversations, manual text imports, local model inference, draft review, orders/bookings, work boards, manually recorded payments, customer history, and analytics.

**Needs internet:** initial downloads, new Facebook messages, fresh Meta profile lookups, and the public tunnel. Facebook does not work offline. Phone access still requires a local connection to the running Mac. Cloudflare transports messages; it does not run AI. Privacy means avoiding an additional cloud AI provider, not that Messenger messages never enter the cloud.

## About-one-minute narration

> Maraming local sellers ang tumatanggap ng orders sa Facebook. Pero kapag pabago-bago ang quantity, pickup time, o booking dates, mahirap bantayan ang bawat chat habang inaasikaso ang negosyo.
>
> Meet BentaBuddy, your Facebook Page business buddy. It turns customer conversations into organized orders and bookings using AI running on our own Mac mini.
>
> Here, the customer changes two dozen pandesal to three dozen. BentaBuddy drafts 36 pieces, shows the source messages, and lets the owner review before approval. The order then appears in preparation.
>
> The same app supports gadget shops, staycation hosts, and service businesses, with customer history and analytics.
>
> Internet down? Saved messages, manual imports, AI extraction, and business workflows still work locally. New Facebook messages need internet.
>
> BentaBuddy: usap to order, less hassle, ka-negosyo.

Time the narration against your recording and trim as needed. Label fictional records and cuts/time compression. Show actual model results rather than generated UI footage standing in for a working demo.

## Validation and scope

At the October 10 documentation update, **52 automated tests and the production build pass**. Separate real model checks passed core order scenarios and all four business themes using temporary databases and CPU CLI inference. They do not establish general accuracy or verify production HTTP/browser behavior. The owner separately confirmed live Messenger receipt, profiles, corrections, and offline operation during development. See [AI validation](docs/AI_VALIDATION.md).

Public-customer Facebook access remains dependent on Meta permissions and approval. An eligible-account demo does not establish public access. The app currently has no sign-in and is a single-owner local prototype. Automatic replies, social posting, payment verification, stock tracking/forecasting, and courier integration are outside scope.

## Submission references

- Repository: [GABlane/BentaBuddy](https://github.com/GABlane/BentaBuddy)
- Setup and implementation: [README.md](README.md)
- Model, tools, assets, and sample-data disclosures: [docs/DISCLOSURES.md](docs/DISCLOSURES.md)
- Logo/video creative direction: [BENTABUDDY_CREATIVE_BRIEF.md](BENTABUDDY_CREATIVE_BRIEF.md)

Add the team's actual names, final video URL, and required social-post URL to the submission form. This file does not publish or submit anything.
