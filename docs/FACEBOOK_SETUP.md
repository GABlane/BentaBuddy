# Connect a Facebook Page to BentaBuddy

The steps below use the team's test Page, The Bakery Dev, as an example. The owner confirmed live receipt and customer profiles during development. Each new installation still needs its own authorized Page, credentials, subscriptions, and permissions. Current prototype scope: [README.md](../README.md).

The Page and Meta app are created. The Messenger API Settings screen has two independent setup sections: configuring the webhook and connecting a Page. Complete both, then subscribe the Page to message events.

## 1. Connect the Page in Meta

Scroll down under **Generate access tokens** and choose the button to connect a Facebook Page. Select your Page and complete Meta's authorization prompts using the account that manages it. Note the numeric **Page ID**. The generated Page access token is a secret; do not post it to chat or GitHub. Optional replies answer status questions using local AI and saved records, or send fixed receipts and owner-triggered status notifications when enabled in Settings; see [auto-reply setup](FACEBOOK_AUTO_REPLY.md). Optional profile lookup uses a backend-only Page access token saved by the profile configuration helper below.

## 2. Save credentials locally

Open the app's **App settings → Basic** to find the **App Secret**. From the BentaBuddy project folder in your Mac Terminal, run:

```bash
.venv/bin/python -B scripts/configure-facebook.py
```

Enter the App Secret at the hidden prompt and the numeric Page ID. The script preserves other `.env` settings, writes these credentials to the ignored local `.env` file with owner-only permissions, and prints a generated **Verify token**. Keep that token for the Meta form. Do not confuse the Verify token, App Secret, and Page access token: they are different values.

Stop the running BentaBuddy app with Ctrl+C and restart it to load `.env`:

```bash
./scripts/start.sh
```

## 3. Start the public webhook connection

Keep BentaBuddy running. In a second Terminal, from the same project folder:

```bash
./scripts/start-facebook.sh
```

This first checks the backend's verification handshake, starts a local webhook-only relay on loopback port 8001, and launches a Cloudflare Quick Tunnel. On Apple silicon it downloads the official cloudflared binary into `.runtime/` if needed. Installation and tunnel operation require internet. The owner confirmed live tunnel operation during development; verify the newly printed callback address for your current session.

Find the generated `https://….trycloudflare.com` address in the output. Your **Callback URL** is that address followed by:

```text
/api/facebook/webhook
```

Only GET and POST to that exact webhook path are forwarded. The dashboard, management APIs, and inference server are not exposed by this relay. Cloudflare transports webhook traffic; AI interpretation and storage remain on the Mac.

## 4. Finish the Meta form

On **Messenger API Settings → Configure webhooks**:

- **Callback URL:** generated HTTPS address plus `/api/facebook/webhook`.
- **Verify token:** exact token printed by `configure-facebook.py`.
- Leave the optional client certificate switch off for this setup.
- Click **Verify and save**.

Complete the connected Page's webhook subscriptions and enable **messages**. If Meta shows the Page connection/subscription in a separate section, complete it there as well. Saving the app callback alone does not guarantee that the Page is subscribed.

## 5. Test a real message

In development, use a personal Facebook account with the administrator/developer/tester role on the Meta app (the Messenger setup screen explains this restriction). Send the Page a synthetic order as that personal profile. Messages sent as the Page are echoes and are ignored.

Open BentaBuddy → **Inbox**. The app opens directly in the live workspace. A received text message should appear and queue local inference. Review and approve the proposal, then open its scheduled work date. Auto-reply is off by default; optionally enable local-AI status replies and workflow notifications in Settings. Use the local preview first.

Keep both Terminals open. The Quick Tunnel address is temporary and changes when restarted; update the Meta callback URL and verify again if it changes. Internet is required for new Facebook events; previously received text and the local bakery workflow continue without it.

## If verification fails

- Ensure both BentaBuddy and the tunnel are running.
- Ensure BentaBuddy was restarted after saving `.env`.
- Use the full HTTPS callback URL including `/api/facebook/webhook`.
- Use the generated Verify token, not the App Secret or Page access token.
- See `data/facebook-relay.log` for relay startup errors. Files under `data/` remain ignored.

Implementation checks include signed-byte preservation, challenge forwarding, relay route restrictions, deduplication, and failure handling. The full project suite has 87 passing tests; model responses and outbound sends in automated tests are mocked. Six separate real local-model checks cover customer status-reply selection. The owner confirmed live verification, tunnel operation, and receipt during development; live outbound replies remain to be verified after restart. Validate access with the actual accounts used in your demo; public access is not implied. See [reply setup](FACEBOOK_AUTO_REPLY.md).

Sources: [Meta Messenger API documentation](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api), [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).


## Customer names and photos (optional)

The webhook supplies a Page-scoped sender ID; names/photos require a separate Meta User Profile API lookup. Generate a new Page access token for The Bakery Dev in Messenger API Settings. Keep it private, then run:

```bash
.venv/bin/python -B scripts/configure-facebook-profile.py
```

Paste the Page access token at the hidden prompt. This preserves the existing webhook verification token, App Secret, and Page ID. Restart BentaBuddy with `./scripts/start.sh`; leave the tunnel running so the callback address stays the same. Send another message from your personal app-role account to capture its sender ID, then allow the profile lookup to finish. Existing records created before profile support need a new message because the original sender ID was not stored.

Names/photos appear in Inbox, Customers, and customer rankings when Meta allows access. Linked order names update too, without changing quantities, workflow state, or versions. Settings → **Refresh customer profiles** retries stored sender IDs. Failed lookups retain the last cached name/photo or the placeholder; messages and local extraction continue working.

`META_PAGE_ACCESS_TOKEN` is backend-only and remains in the ignored local `.env`. The default Graph API version is `v22.0`; `META_GRAPH_VERSION` can be set to a supported version. Profiles refresh after one day on the next incoming message; unsuccessful lookups retry after an hour or on manual refresh. Photos are downloaded from approved Meta CDN hosts (JPEG/PNG/WebP, maximum 2 MB) into ignored `data/facebook-profiles`, served through the local app (which currently has no sign-in), and remain available without internet. No token or remote photo URL is returned to the browser. Profile lookup is internet-dependent; inference remains local.

Validation: automated tests cover profile success, denied access, image host/size restrictions, token isolation, cached-photo serving, and preservation of order fields. The owner confirmed live profiles during development; other accounts/installations still need permitted access. Cached photos are accessible through the local application, which currently has no sign-in.
