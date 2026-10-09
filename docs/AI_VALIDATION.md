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
