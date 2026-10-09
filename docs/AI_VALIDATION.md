# Local extraction validation — October 9, 2026

## Failure and correction

The original Ollama `qwen3:4b` blob identified itself in GGUF metadata as **Qwen3 4B Thinking 2507**. Its chat template always opened a thinking block. The runtime logs showed repeated requests consuming all 2,200 output tokens, with approximately 73 seconds of generation per request. The app then tried to decode empty final content as JSON and displayed `Expecting value: line 1 column 1`.

The default is now pinned to **qwen3:4b-instruct-2507-q4_K_M**, a non-thinking Instruct variant. Blob SHA-256 verified: `85e4a5b7b8ef0e48af0e8658f5aaab9c2324c76c1641493f4d1e25fce54b18b9`. Thinking is also disabled in startup and request settings. The parser rejects empty/truncated responses with a useful error and never treats reasoning as an order. Dates and times have schema patterns, source timestamps provide a deterministic calendar for “bukas,” and the prompt explicitly applies later corrections within one message. The first real Instruct run exposed a wrong time and timestamp-shaped date; the final prompt/schema changes below corrected those cases.

Sources: [Qwen's Thinking-only model card](https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507), [pinned Instruct distribution](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M).

## Actual model tests

These are real model generations, not prewritten proposals. Used the pinned GGUF, the application's system prompt/context/schema, and llama.cpp b11429 `llama-completion` in one-shot **CPU-only** mode on this Mac. The model transport was replaced with the CLI because this coding session cannot reach local server ports or initialize a Metal command queue. Backend parsing, source evidence validation, catalog normalization, owner approval, and order revision executed against a temporary SQLite database. No real customer data or saved bakery orders were changed.

| Input / operation | Verified result | Wall time including model load |
| --- | --- | --- |
| “Ate, pa-order 2 dozen cheese pandesal bukas, pickup 8am. Gawin na lang 3 dozen, 9am na lang po.” Timestamp October 9, 2026, 17:26 Manila | New order, 36 pieces, October 10, 09:00 pickup | 16.36 seconds |
| Linked-order follow-up: “Gawin na lang 4 dozen cheese pandesal. Same pickup date and time po.” | Revision on the same order ID, 48 pieces, October 10 at 09:00 preserved | 19.30 seconds |
| “Magkano po cheese pandesal? Available po ba bukas?” | Inquiry, not an approved purchase | 18.23 seconds |

All three passed. These timings do not measure the production server's Metal performance and are not a general accuracy benchmark. Nineteen automated workflow/parser/authentication tests also pass; model responses in that automated suite are mocked.

## Reproduce against the running model server

Stop the old app/model, then run `./scripts/start.sh` so the replacement model loads. From a second Terminal:

```bash
cd BentaBuddy
.venv/bin/python -B scripts/check-ai.py
```

This uses the real localhost HTTP transport and an isolated temporary database; it does not need the bakery password or modify real records. It exits with an error if a result is wrong. The optional `--cli /path/to/llama-completion` mode reproduces the one-shot CPU test above but does not exercise HTTP.

Production HTTP extraction and visual browser behavior after the restart remain unverified in this session. Model inference on the three synthetic cases is verified.


## Request-boundary regression — October 9, 2026

The extractor previously sent the last 25 chat messages, which could replay previous purchases. It now sends only messages since approval (or an owner-selected new-purchase boundary). Active approved orders remain revision context; closed orders are excluded. Source evidence is validated against the scoped messages. With no unreviewed messages, extraction stops visibly rather than replaying an approved request. Full chat history and earlier orders remain stored.

The extended `scripts/check-ai.py --cli .runtime/cli-check/llama-b11429/llama-completion` passed all four actual local CPU cases after this change. The existing corrected-order, revision, and inquiry checks passed again (18.03, 20.13, and 20.52 seconds including model load). A fourth case completed the pandesal order, appended “Pa-order naman 3 chocolate chip cookies bukas, pickup 10am.” to the same conversation, and produced only 3 cookies for October 10 at 10:00. Approval created a different order ID with the same customer; no old pandesal items were included. The fourth case was not individually timed. This remains a CLI transport check, not a production browser test.

All 32 automated tests pass, including request boundaries, legacy approval recovery, closed-order isolation, separate purchases preserving open orders/customer identity, stale scope selection, and rejection of old-message evidence. The owner previously confirmed live Messenger delivery/profiles and offline operation; the updated request-boundary UI still needs their browser check after restart.

## Business workflows — October 10, 2026

The business workflow suite now contains 48 passing automated tests, including nightly totals, invalid dates/guest counts, overlapping confirmed bookings, adjacent stays, different units, cancellation/completion releasing dates, pending-to-confirmed validation, simultaneous confirmations, and persistence of bakery packaging, gadget variants, and service locations. Tests run against isolated databases.

The new `scripts/check-business-ai.py` exercises actual Qwen3 4B Instruct inference for each theme in an isolated database. Initial CPU checks passed bakery (2 dozen pandesal with gift-box notes) and gadgets (2 USB-C cables with black-color notes). The first staycation attempt omitted structured reservation details; a later concurrent CPU run timed out, and a general-business run returned invalid JSON. The extractor now gives staycation a booking object schema with explicit unknown fields, and keeps the smaller order schema for other businesses. A sequential staycation retest passed: studio unit, 2 guests, November 20–22, 2026, 2 nights, pending status. A general-business retest recognized the service but omitted its location; the prompt was tightened to preserve explicit service-location details.

These CLI checks use real model inference but do not verify the HTTP model transport or the browser. Live browser validation after restarting BentaBuddy remains outstanding.

The final sequential general-business retest passed after the prompt change: one service on November 20 at 10:00, with `service location: customer office` retained in notes. Across the completed CLI checks, all four business themes produced valid, source-backed drafts. The CLI smoke test now also asserts bakery gift-box notes, gadget black-color notes, and service-location notes, in addition to accommodation dates/guests.

## Output-limit investigation — October 10, 2026

The latest recorded failed extraction at 06:36 Manila took 76.29 seconds and exhausted 2,200 generated tokens. The correct Instruct model was already running; changing models was not the immediate fix. The request included unreviewed follow-ups and an open approved order.

The extraction prompt now requests concise drafts with explicit action definitions, limits notes/questions/source quotations, and constrains product IDs and source message IDs to the supplied catalog and messages. Approved-order context excludes payment history and customer metadata. Queued jobs retain the business kind selected when extraction was requested. Explicit separate-purchase phrases alongside an open order constrain the generated action to clarification with no combined item list; the owner must select the purchase boundary.

Initial actual-model checks exposed an extra unrequested catalog item and a correction labeled as a new order. Explicit catalog grounding and revision instructions corrected those cases in subsequent checks. Prompt instructions alone still merged explicit separate purchases, which led to the schema safeguard above. These are targeted regression checks, not an accuracy guarantee for arbitrary conversations. Tests use synthetic records in temporary databases; no customer orders are approved or changed by them.

The core CPU CLI run passed five cases: corrected new order (20.32 seconds), revision of the same order (23.70 seconds), inquiry (19.03 seconds), returning customer without replaying closed purchases, and four conflicting follow-ups asking for a separate purchase (35.24 seconds, clarification rather than revision). Fifty-two automated tests and the production frontend build pass. The running HTTP server and browser remain unverified from this coding session; restart the app to load the backend changes.

The subsequent theme checks exposed two additional issues: a repeated gadget line and a service location omitted from notes despite appearing in the address field. Repeated product IDs now retain one suggested line and require explicit quantity clarification rather than adding the duplicate to the total. The prompt specifies one line per product and requires service locations in notes. Theme smoke assertions now check exact line count and quantity as well as product identity.

The final sequential four-theme CPU CLI run passed the stronger assertions: bakery 2 dozen pandesal with gift-box notes, gadgets exactly 2 USB-C cables with black-color notes, staycation exactly 2 nights for November 20–22 with 2 guests and pending status, and general service exactly 1 service with `service location: customer office` in notes. None of these checks verifies browser behavior or HTTP transport.
