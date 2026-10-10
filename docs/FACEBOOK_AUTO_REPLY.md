# Facebook replies and status updates

BentaBuddy supports three optional reply modes. All are off by default. Local Qwen can interpret a customer status question and select a reply about that customer's saved order. The backend writes the factual status text. Owner-triggered workflow notifications and fixed receipts use saved records/templates directly, without model inference.

## Set up and preview

1. Complete [Facebook setup](FACEBOOK_SETUP.md), including the Page subscription and verified webhook callback. Confirm a fresh eligible message reaches Inbox.
2. Save a Page access token with `.venv/bin/python -B scripts/configure-facebook-profile.py` if needed. It must permit messaging for your configured Page. Keep credentials private.
3. Restart using `./scripts/start-phone.sh` for phone access or `./scripts/start.sh` for Mac-only access. Refresh the browser. Keep the local model and webhook tunnel running.
4. Open **Settings → Facebook replies & status updates**. Under **Try a local reply without sending**, select a customer conversation and enter `Ano na po status ng BB-1001?`, replacing the number with that customer's saved order number. Click **Preview local AI reply**. This only calls local inference; it sends nothing to Meta and works offline with the model running.
5. Enable **Enable replies to new Page messages**. Enable **Use local AI for customer status questions** for grounded answers, and **Notify customers when I approve or update an order / booking** for workflow notifications.
6. Test a fresh question from an eligible account using fictional order details. Check Messenger and **Recent replies**. Update that order's kitchen/dispatch or booking state and check the resulting notification.

Turning off the master setting prevents new replies. An already in-flight network send may still complete. Enabling replies does not replay saved messages or old workflow changes.

## What customers receive

| Trigger | Result |
| --- | --- |
| `Luto na po yung BB-1001?` | Saved bakery kitchen state, item summary, and scheduled handoff |
| `Na-dispatch na po BB-1002?` | Saved dispatch state; no invented courier location or arrival time |
| `Confirmed na ba booking BB-1003?` | Saved pending/confirmed/check-in/completed state, dates, and guests |
| Several possible orders without a clear reference | Asks for an order number or distinguishing item/schedule |
| Unknown order number | Asks for clarification; does not disclose another customer's order |
| New purchase, edit, cancellation request, greeting, or price question | Receipt for shop review; does not approve or change an order |
| Owner approval or workflow update | Notification from the newly saved status |
| Local inference unavailable or invalid reply selection | Receipt asking the customer to wait for the shop |

The model receives at most ten recent orders belonging to the exact customer ID, excluding demo records. A strict JSON schema limits it to allowed reply IDs. Status wording is rebuilt from the latest saved order before sending. This is bounded status assistance, not unrestricted generated chat. Pending bookings explicitly remain unconfirmed. Stock, live ETA, payment verification, and new availability promises are outside this feature. Owners must keep workflow states current; the app has no kitchen sensors or courier tracking.

## Delivery behavior

- Receipt-only mode has a 15-minute per-Page/customer cooldown. AI mode replaces unfinished replies when follow-up messages arrive and uses a five-second send cooldown to limit bursts. Messages suppressed by cooldown are still saved; they may not get an individual reply.
- Only signed, configured-Page text events with usable sender IDs and recent timestamps qualify. Echoes and duplicate message IDs do not generate new replies.
- Model access is serialized with extraction. Replies may wait for an existing local inference task.
- Before sending, queued replies recheck settings, Page, credentials, and age. Changed conversation versions invalidate unfinished AI answers. Outdated workflow notifications are skipped.
- Workflow notifications are deduplicated per order version and queued after the owner transaction commits. Notification failure does not undo an order change. Payment-only changes do not trigger notifications.
- Outbound text is stored separately from incoming text and never re-extracted as a customer request.
- Failed/uncertain sends are not automatically retried. Restart marks unfinished work failed instead of replaying it.
- **Accepted by Meta** means the Send API returned a message ID, not proof of delivery/read. Local errors omit tokens and raw remote error bodies.

## Meta requirements and troubleshooting

The Send API requires a Page token and appropriate `pages_messaging` access. This implementation uses `messaging_type: RESPONSE` and only sends within 24 hours of an eligible incoming customer text. Internet is needed for Messenger transport; local inference, preview, saved records, and workflows remain available offline. See [Meta's official Messenger API collection](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api).

Enabling a setting does not grant public-customer access. App permissions and access mode still apply. If no reply appears, check **Recent replies**, the toggles, fresh webhook receipt, token/Page match, response window, and cooldown. Keep BentaBuddy and its verified tunnel running. Consider disabling overlapping Meta Business Suite instant replies to avoid duplicate acknowledgments.

## Validation

The suite passes **87 automated tests**, covering isolated customer context, local preview without sends, model fallback, pending/confirmed/check-in/completed booking notifications, latest-status rechecking, follow-up replacement, toggle/configuration changes, duplicate/echo handling, cooldowns, expired windows, concurrent claims, and failure/restart behavior. The production frontend build passes.

Six real Qwen CPU CLI checks passed for kitchen, dispatch, pending booking, ambiguous orders, a new purchase, and an unknown order reference. Reproduce with:

```sh
.venv/bin/python -B scripts/check-customer-replies.py --cli /path/to/llama-completion
```

The script uses fictional records and never calls Meta or the live database. HTTP sends in the automated suite are mocked. These checks do not establish running-server/browser behavior or live Messenger delivery; verify those after restart using the steps above.
