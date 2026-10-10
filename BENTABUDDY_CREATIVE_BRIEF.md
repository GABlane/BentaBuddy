# BentaBuddy — App concept, logo prompt, and demo-video brief

Paste this entire document into an AI chatbot, designer, or video-production assistant. Use the logo and video sections as separate prompts if needed.

## Your task

Act as a brand designer and demo-video director. Help create a distinctive logo and a convincing 60-second hackathon demo for **BentaBuddy**, a local-AI business assistant for Filipino sellers who receive orders through Facebook Pages. Use the product facts below. Present capabilities accurately and use fictional customer information in any generated visuals.

Deliver:

1. Three logo concepts, a recommended direction, and a final logo-generation prompt.
2. A 60-second storyboard with shot descriptions, on-screen text, and Taglish voiceover.
3. A screen-recording checklist and prompts for any supplemental generated video clips.

If you have image/video generation tools, produce the assets you can. Otherwise, provide ready-to-use prompts and editing instructions. Do not claim files or videos were generated unless they actually were.

## The idea in one sentence

**BentaBuddy turns messy Facebook Page conversations into organized orders and bookings, using AI that runs on the business owner's own computer.**

Product descriptor: **Your Facebook Page business buddy.**

Possible tagline: **Usap to order. Less hassle, ka-negosyo.**

Use **BentaBuddy** as the product name. “Facebook Page business buddy” explains its purpose; it is not the official product name or a claim that Meta owns or endorses the app.

## The problem

A small business owner receives messages like:

> “Ate, pa-order 2 dozen cheese pandesal bukas, pickup 8am po.”
> “Gawin na lang 3 dozen, 9am na lang.”

The owner must remember the latest quantity, date, time, delivery details, and special requests while preparing products or serving customers. Requests are scattered across conversations, and corrections can lead to missed orders or incorrect preparation.

A gadget seller faces model/color and dispatch details. A staycation host needs guest counts, dates, and protection against overlapping confirmed bookings. A service provider needs schedules and locations.

## How the product works

1. Connect a Facebook Page the owner manages, or paste a customer conversation manually.
2. Incoming supported text messages appear in BentaBuddy's inbox.
3. Local AI reads the current request, including Taglish and corrections, against the business catalog.
4. The app proposes structured details and supporting message excerpts. Missing information becomes a clarification question.
5. The owner reviews, edits, and approves. AI does not independently confirm a sale or booking.
6. The approved request becomes an order or reservation in the appropriate workflow.
7. The owner tracks fulfillment, manually records received payments, and views customer/order analytics.
8. With optional replies enabled, local AI matches status questions to that customer's saved orders. The backend supplies the recorded kitchen, dispatch, or booking status. Owner workflow updates can also notify the customer through Messenger while online.

Think of it as an **operations assistant for a Facebook Page**, rather than a replacement for every Facebook Page management feature.

## Who it serves

| Business | Relevant catalog | Workflow |
| --- | --- | --- |
| Bakery / food seller | Bread, pastries, cakes, food services | Quantities, pickup/delivery, packaging instructions, kitchen preparation |
| Gadget shop | Devices, cables, accessories, setup services | Model/color/variant details, packing, dispatch, handoff |
| Staycation host | Individual accommodations, guest extras, services | Check-in/out, guests, calculated nights, pending/confirmed bookings, check-in and completion |
| General seller / service provider | Products, services, packages | Scheduled work, service location, fulfillment |

Switching business themes changes the visual style, catalog, and relevant workflow wording. Starter offerings have labeled example prices, which the owner can customize. Saved edits remain when switching back.

## The local-AI advantage

- The current prototype runs its web app, database, and AI on a Mac mini.
- A phone can open the responsive website over the same local Wi-Fi or hotspot. The phone is a browser client; the AI runs on the Mac.
- Qwen3 4B Instruct runs locally through llama.cpp. The app uses a pretrained model; do not describe it as a model trained from scratch by the team.
- Saved messages, manual imports, AI extraction, status-reply preview, orders, and analytics can work without internet once the app and model are installed.
- Facebook message delivery requires internet. New Messenger messages and outbound replies/notifications do not work while disconnected.
- Local inference avoids sending the conversation to an additional cloud AI provider. Facebook and the connection tunnel still transport Page messages when online.

## What the prototype includes

- Inbox with imported or Facebook Page text conversations.
- Owner-reviewed AI proposals with supporting message excerpts.
- Business-specific catalogs and themes.
- Orders, preparation/dispatch/work boards, customers, and analytics.
- Manual payment recording; a customer's claim of payment is not verification.
- Staycation reservation dates, guest counts, calculated nights, and server-side overlap checks when confirming or editing bookings.
- Pending booking requests do not block dates. Each accommodation catalog entry represents one bookable unit; separate rooms need separate entries.
- Optional local-AI status replies and owner-triggered kitchen/dispatch/booking notifications, off by default. The AI selects a bounded reply; code writes the saved status. Preview works offline without sending.

## Boundaries to respect in the logo/video

Do not show unsupported features as finished:

- Unrestricted generated chat, automatic order/booking confirmation, post publishing, ad management, or comment moderation. Optional local-AI status replies select grounded responses from the customer’s own records; owner-triggered kitchen/dispatch/booking notifications and fixed receipts are also implemented, off by default. Outbound delivery still needs live Page verification.
- Automatic payment verification, payment collection, or courier integration.
- Gadget inventory tracking or automatic stock verification.
- Accommodation capacity pools or automatic guest-limit enforcement.
- Facebook message delivery while offline.
- AI running directly on the phone.
- A public Facebook integration already approved for unrestricted customers. The current prototype is tested with eligible app-role accounts; broader access depends on Meta permissions/review.
- Several independent shops or Facebook Pages connected at once. Themes adapt one local installation; they are not separate tenant accounts.

Sample orders and example prices are demonstration material, not actual sales, revenue, or customer demand. Use the existing sample labels in recordings.

## Logo-generation prompt

Create a logo for **BentaBuddy**, an approachable business assistant for Filipino entrepreneurs who sell through Facebook Pages.

The core idea is: **a customer conversation becomes a clear, owner-approved order**. Explore an original chat-bubble symbol with a subtle “B” and an integrated check or order slip. The symbol should feel like a helpful buddy and a useful business tool. Keep it simple enough to recognize as a mobile app icon or small dashboard mark.

The brand must work equally well for bakeries, gadget shops, staycation hosts, and service providers. Do not make bread, a phone, or a house the main brand symbol. Business-specific icons belong to the themes, not the master logo.

Style:

- Clean, modern, friendly, and practical.
- Rounded geometry with a clear silhouette and generous negative space.
- A readable wordmark spelling exactly **BentaBuddy**.
- One distinctive visual idea; avoid cluttering the icon with multiple tiny symbols.
- No Facebook “f”, Messenger lightning mark, Meta infinity mark, or copied existing logo.
- Avoid Philippine-flag decoration and generic robot brains; express local friendliness through tone and warmth.

Suggested master palette: deep forest green `#244C36`, warm cream `#F5F6F0`, and muted gold `#D6AE62`. The mark must also work in one color and on light or dark backgrounds. Secondary theme colors are violet for gadgets, teal for staycations, and amber for general businesses.

Present three directions first:

1. Chat bubble + subtle B + approval check.
2. Conversation bubble transforming into an order slip.
3. A simple abstract buddy symbol with a business/task cue.

Recommend the most distinctive direction, then provide:

- Horizontal symbol + wordmark.
- Square app icon with no text.
- One-color version.
- Light-background and dark-background versions.
- Transparent PNG exports; SVG if your tools can produce genuine vector artwork.

Show the final mark flat and clearly before displaying optional mockups. Keep any tagline outside the small app icon. Do not substitute a mockup for the actual logo asset.

## Demo-video creative direction

Goal: a judge should understand the problem, see a real working message-to-order flow, and understand why local AI matters within one minute.

Tone: confident, warm, practical, Filipino. Avoid exaggerated claims about revenue, productivity gains, or accuracy. Show the workflow instead of inventing statistics.

Format: 60 seconds, 16:9 landscape, 1080p. Keep important content within the center area so a portrait cut can be made later. Use readable captions and restrained transitions.

Use actual screen recordings for product behavior. Generated clips may support the opening and closing, but must not imitate unrecorded features or fabricate a successful extraction.

### 60-second storyboard

| Time | Visual | On-screen text | Purpose |
| --- | --- | --- | --- |
| 0–6s | A Filipino small-business owner juggling customer messages and a handwritten order list. Use fictional messages. | “Orders buried in chat?” | Establish the problem quickly. |
| 6–11s | BentaBuddy logo, then the actual inbox. | “Meet BentaBuddy.” / “Your Facebook Page business buddy.” | Introduce the product. |
| 11–23s | Show the pandesal request and its quantity/time correction. Run local extraction and reveal 3 dozen / 36 pieces / 9 AM. Show a supporting excerpt briefly. | “Reads Taglish. Follows corrections.” | Demonstrate useful local AI. |
| 23–31s | Owner reviews and approves. Open the saved order and kitchen list for the scheduled date. | “You review. You approve.” | Establish owner control and the operational result. |
| 31–41s | Fast, readable cuts: gadget catalog and dispatch; staycation dates and night total; general-service location. Use prepared sample records. | “Bakery • Gadgets • Staycation • Services” | Show adaptation across businesses. |
| 41–46s | In staycation, attempt to confirm a prepared overlapping booking and show the real conflict message. | “Checks booking overlaps.” | Show a concrete safeguard. |
| 46–55s | Disconnect the Mac's internet during a localhost demo. Paste a fresh message manually and run extraction. Reveal the resulting draft. | “AI runs on your computer.” / “Saved work + manual imports work offline.” | Prove the local-AI advantage honestly. |
| 55–60s | Logo over a clean dashboard/end card. | “BentaBuddy” / “Usap to order. Less hassle, ka-negosyo.” | End with a memorable product promise. |

If inference takes longer than its allocated video segment, trim or speed up the recording and label it **“Processing shortened”**. Do not imply the edited clip measures real-time latency. A backup recording is useful, but present it as recorded footage if used during a live demo.

### Optional status-reply segment

For a longer demo, show the customer asking “Luto na po yung BB-1001?” using the saved order's actual number. Show the local AI selecting the recorded kitchen status. Then change the order to ready/dispatch and show the resulting notification. A staycation version can show that a pending booking is explicitly unconfirmed before the owner confirms it. Do not show an invented ETA, automatic booking approval, or kitchen/courier sensing.

Use **Settings → Facebook replies & status updates → Try a local reply without sending** for a local-only preview. Label it as preview. Only show a received Messenger reply as working live delivery after verifying it with the configured Page and an eligible account. Sending needs internet; offline footage can demonstrate preview but not live Facebook transport. Setup: [Facebook replies](docs/FACEBOOK_AUTO_REPLY.md).

### Suggested Taglish voiceover

“Pa-order po… tapos may bagong quantity, oras, at delivery details. Kapag nasa chat lahat, madaling may makaligtaan.

Meet BentaBuddy—ang business buddy ng Facebook Page mo.

Binabasa ng local AI ang Taglish messages at corrections, then ginagawa itong malinaw na order draft. Ikaw pa rin ang nagre-review at nag-a-approve.

Pag approved, nasa kitchen o dispatch list na. May workflow din para sa gadget shops, staycation bookings, at services. Sa staycation, kinukuwenta ang nights at chine-check ang overlapping confirmed bookings.

At kapag nawalan ng internet? Saved messages, manual imports, at AI extraction, tuloy pa rin sa computer mo. New Facebook messages need internet.

BentaBuddy. Usap to order. Less hassle, ka-negosyo.”

Adjust the pacing to fit 60 seconds naturally; shorten sentences before speeding the voice unnaturally. Match each claim to the visible recording.

## Recording checklist

Before recording:

- Start BentaBuddy and the local model; verify model readiness.
- Choose the primary business theme and use clearly labeled sample customers/orders.
- Use a fictional customer name, address, profile picture, and message text.
- Set explicit demonstration dates so “bukas” does not become confusing on another day.
- Prepare one gadget order, one general service request, and two overlapping requests for the same accommodation.
- For the booking safeguard, confirm the first request, then attempt to confirm the second. Two pending requests alone do not create a conflict.
- Use a catalog entry that represents a single room/unit.
- Keep App Secrets, access tokens, verify tokens, login passwords, developer dashboards, personal chats, and terminal environment output out of the recording.
- Test the actual workflow before filming. Do not invent a screen if an interaction fails.

For the offline shot:

1. Use the website on the Mac through `http://127.0.0.1:8000`.
2. Ensure the app, model, and assets are already installed locally.
3. Disconnect internet while keeping the app and local AI running.
4. Paste a new fictional conversation manually and extract it.
5. Show the resulting proposal and owner review.
6. State that new Facebook messages still require internet.

For a phone shot, keep the phone and Mac on a working local network. Do not demonstrate offline capability by breaking the local network the phone needs to reach the Mac.

## Supplemental generated-video prompt

Create a short, natural opening clip for a Filipino small-business software demo: a local entrepreneur at a modest, tidy workspace, switching attention between customer chats and a paper order list. Warm daylight, believable everyday setting, respectful representation, no exaggerated poverty imagery. Frame a clean area for captions. Avoid readable real customer data, brand logos, or fake app interfaces. No baked-in text. This clip establishes the problem; actual BentaBuddy screen recordings will demonstrate the solution.

## Final quality check

- Can viewers explain BentaBuddy after one viewing?
- Does the logo work beyond the bakery theme?
- Is the owner visibly in control of approvals?
- Does the video distinguish local AI from Facebook message transport?
- Are offline claims demonstrated accurately?
- Are generated visuals clearly separate from real product behavior?
- Are sample records distinguishable from actual customer activity?
- Is the finished video easy to follow on a phone screen?
