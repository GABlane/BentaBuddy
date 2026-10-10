# BentaBuddy — step-by-step setup

This guide starts from a fresh checkout. The bundled setup targets **Apple silicon macOS**; the demo was developed on an **M4 Mac mini with 16 GB memory**. Other systems need a compatible local runtime; see the Ollama alternative below. Facebook is optional: you can reproduce the core AI workflow using manual imports without a Meta account.

## 1. Check prerequisites

Install Git, Node.js 22 or newer (including npm), and Python 3.9 or newer. Open Terminal and check:

```bash
git --version
node --version
npm --version
python3 --version
uname -m
```

For the bundled Mac runtime, `uname -m` should print `arm64`. Have internet available for the initial dependency and model downloads. Allow several GB of free disk space for the model, runtime, dependencies, and build. Download time depends on your connection.

## 2. Clone and enter the repository

```bash
git clone https://github.com/GABlane/BentaBuddy.git
cd BentaBuddy
```

If you already have a checkout, open Terminal in that existing project folder instead. All commands below run from the **repository root**, which contains `package.json`, `backend/`, and `scripts/`.

## 3. Install the app and local model

```bash
./scripts/setup.sh
```

The script creates `.venv`, installs locked Python and npm dependencies, builds the frontend into `dist/`, downloads the bundled llama.cpp runtime and Qwen3 4B Instruct GGUF, and verifies the model checksum. Wait until it finishes successfully and prints `Ready. Run ./scripts/start.sh`.

The default model alias is `qwen3:4b-instruct-2507-q4_K_M`; the weights are stored at `.runtime/models/qwen3-4b-instruct-2507.gguf`. No cloud AI API key is needed. A `.env` file is **not required** for the default manual-import/local-AI demo.

## 4. Start BentaBuddy

```bash
./scripts/start.sh
```

Open **http://127.0.0.1:8000** on the Mac. Keep this Terminal open. Startup launches the local AI if the configured model is not already running; model loading may take a little time. Open **Settings → Local AI model** and use **Check model connection** until it reports ready.

The app opens without login. It is a single-owner prototype. The model endpoint stays at `127.0.0.1:11434`. A fresh install creates starter catalogs, not historical customer orders. The app/database are local; internet is no longer required for this manual-import workflow after installation.

## 5. Set up your business

In **Settings**, enter a business name and select Bakery & food, Gadget shop, Staycation, or General business. Save, then open the catalog.

Edit offerings, aliases, prices, and availability to match your business. Starter prices are examples. Only active offerings in the relevant catalog are supplied to extraction. For stays, create one accommodation entry per individual bookable unit; a nightly price alone does not reserve dates.

## 6. Verify the core AI workflow

For a first check, select Bakery & food and leave Cheese pandesal active. Open **Inbox → Import message**, use a fictional customer name, and paste:

```text
Ate, pa-order 2 dozen cheese pandesal bukas, pickup 8am.
Gawin na lang 3 dozen, 9am na lang po.
```

Run extraction if it has not already started. Wait for the real model result. Check for 3 dozen / 36 pieces, pickup at 09:00, and tomorrow relative to the imported message date. Inspect the supporting excerpts, correct any mistake, then **Review & confirm**. Open its scheduled work date and verify that the approved order appears. Orders are not created just by receiving a message.

For a separate purchase in the same conversation, choose **Start new order here** on its first message. This keeps the previous open order intact.

Optional labeled sample conversations for all business types:

```bash
.venv/bin/python -B scripts/seed-demo-messages.py
```

Refresh the page afterward. This adds fictional inbox messages, not precomputed AI results. The helper backs up data first. To remove those sample conversations while retaining orders approved from them:

```bash
.venv/bin/python -B scripts/seed-demo-messages.py --remove
```

## 7. Open it on a phone (optional)

Connect the phone and Mac to the same trusted Wi-Fi or local hotspot. Stop the app with **Ctrl+C in its Terminal**, then run:

```bash
./scripts/start-phone.sh
```

On the phone, open the matching **`http://MAC_IP:8000`** address printed by the script. Type `http://` explicitly; do not use `localhost` on the phone. Allow incoming connections on macOS if prompted. Keep the Mac awake and the app running.

The phone is a browser client; inference runs on the Mac. Guest/venue networks may isolate devices, and the Mac's address may change when switching networks. There is no sign-in, so use a trusted network and fictional demo records. The Facebook tunnel address cannot open the dashboard.

## 8. Connect Facebook (optional; internet required)

Skip this section if you are demonstrating manual imports. You need a Page you manage, a Meta app with the Messenger use case, and appropriate access for the account sending test messages. Public-customer access depends on Meta permissions/approval.

1. In Meta's Messenger API settings, connect your Page and note its numeric Page ID. Find the **App Secret** under app settings. The App Secret, Page access token, and webhook Verify token are different values.
2. In Terminal, run the credential helper:

   ```bash
   .venv/bin/python -B scripts/configure-facebook.py
   ```

   Enter the App Secret at the hidden prompt and the Page ID. The helper saves ignored local `.env` settings and prints a generated Verify token. Keep credentials private; do not paste them into the repository or submission.

3. Restart the app with `./scripts/start.sh` or `./scripts/start-phone.sh` to load the settings.
4. Open a **second Terminal**, enter the same repository folder, and run:

   ```bash
   ./scripts/start-facebook.sh
   ```

   It checks the local handshake, starts the webhook relay on loopback port 8001, and opens the tunnel. The first run may download cloudflared.

5. Copy the printed `https://….trycloudflare.com` address. In Meta, set **Callback URL** to that address plus `/api/facebook/webhook`. Set **Verify token** to the exact value printed by the credential helper, then verify/save. Subscribe the connected Page to **messages** as well; callback verification alone is insufficient.
6. Keep both Terminals open. Send a new fictional order from an eligible personal account to the Page. Open Inbox and verify receipt, extraction, review, and approval. Messages sent as the Page are ignored echoes. Historical messages are not imported.
7. For permitted customer names/photos, run `.venv/bin/python -B scripts/configure-facebook-profile.py`, enter a fresh Page access token privately, restart the app, then send a new message or choose **Refresh customer profiles** in Settings.

Restarting the Quick Tunnel can change its URL; update and verify the Meta callback again when that happens. See [FACEBOOK_SETUP.md](FACEBOOK_SETUP.md) for details. Only the webhook route is public through this relay; the app does not send automatic customer replies.

## 9. Demonstrate offline operation

Finish setup and confirm model readiness while online. Keep the Mac/app running, then disconnect **upstream internet** while retaining the local network if using a phone. On the Mac alone, you can use the loopback URL without Wi-Fi.

Paste a fresh fictional request, run extraction, review/approve, and show the saved order/work board. Customer history and analytics remain local. New Facebook messages, profile lookups, and the tunnel need internet and will not keep working offline. Record the real inference; label any cuts or time compression.

## 10. Run project checks

From the root in another Terminal:

```bash
npm test
npm run build
```

With the local model ready, test actual inference in isolated temporary databases:

```bash
.venv/bin/python -B scripts/check-ai.py
.venv/bin/python -B scripts/check-business-ai.py
```

Run the inference scripts sequentially. Automated workflow tests mock AI responses; these two scripts call the actual local model. They do not alter saved customer records. See [AI_VALIDATION.md](AI_VALIDATION.md) for CLI alternatives and validation scope. A fresh installation and live browser flow still need verification on the target machine.

## Restarting, updates, and backups

For later use, run `./scripts/start.sh` or `./scripts/start-phone.sh`; setup is not needed every time. After frontend changes, run `npm run build`. After backend or environment changes, stop/restart the app and refresh the browser. Stop the Facebook tunnel separately with Ctrl+C when finished.

SQLite lives at `data/bentabuddy.sqlite3`. With the app stopped, back up the entire `data/` folder. Preserve `.env` separately and privately for Facebook settings. Do not delete `data/` to troubleshoot a startup or extraction issue.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| `no such file or directory: /scripts/...` | Use `./scripts/...` from the repository root; the leading dot matters. |
| Missing app dependencies or build | Run `./scripts/setup.sh` and resolve its first error before starting. |
| Download failure | Reconnect internet and rerun setup. Do not treat a partial download as completed setup. |
| Model not ready | Wait for loading, check Settings, inspect `data/local-ai.log`. Verify the Instruct model is installed. |
| Different model on port 11434 | Stop the other model process in its own Terminal/app, then restart BentaBuddy. |
| Port 8000 already in use | Stop your earlier BentaBuddy instance before starting another. |
| Phone cannot connect | Use the printed IP/port, same trusted network, phone startup script, and macOS incoming-connection permission. |
| Meta callback cannot validate | Restart the app after saving settings; check the current tunnel URL, full webhook path, and generated Verify token. |
| Your messages arrive, other people's do not | Check app-role acceptance and Meta access/permissions; a working tunnel does not grant public access. |
| Extraction fails or mixes purchases | Check model readiness; retry or select Start new order here for the current purchase. Review unresolved questions. |

## Ollama alternative

The bundled runtime path above targets Apple silicon. With a compatible Ollama installation running on your machine, install the app using the alternative setup branch:

```bash
BENTABUDDY_RUNTIME=ollama ./scripts/setup.sh
ollama pull qwen3:4b-instruct-2507-q4_K_M
```

Then set `BENTABUDDY_RUNTIME=ollama` in your local `.env`, preserving any existing Facebook settings. You may use `.env.example` as a template only if you do not already have `.env`; set the runtime there before starting. Keep the pinned Instruct model alias. Run `./scripts/start.sh`, using the same phone option if desired. Do not run llama.cpp and Ollama simultaneously on port 11434. Platforms beyond the demo Mac require their own runtime/browser verification; this is not a claim of tested Windows/Linux support.
