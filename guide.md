# WhatsApp Integration Guide

Two parts: first-time Meta setup (once), then restart steps (every time).

## Part 1: First-Time Meta/WhatsApp Setup

Do this once, before Part 2 ever applies. Meta's dashboard UI shifts often — if a label below doesn't match what you see, look for the nearest equivalent (the flow's structure has been stable even when button names move).

### 1. Create a Meta app
1. Go to [developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App**.
2. **Naming matters even for testing**: arbitrary names are fine for pure local dev, but this name becomes client-visible later during "embedded signup" flows in production — name it like a real product from the start if there's any chance this goes further than your own testing.
3. Product selection: under **Featured** or **Business Messaging** tabs, select **Connect with customers through WhatsApp**.
4. **Meta Business Portfolio**: select an existing one or **Create Business Portfolio**. New portfolios require a portfolio name plus the legal first/last name of the administrator (this is Meta's current name for what used to be "Business Manager" — it's the entity that owns the WhatsApp asset).
5. Proceed through the verification prompts to finish creating the app.

### 2. Sandbox testing (temporary token)
This is Meta's "Try it out" sandbox — validate your webhook logic here before anything permanent.
1. In the WhatsApp setup dashboard, click **Generate Token**. In the selection dialog, make sure you pick the **WABA (WhatsApp Business Account) ID** that matches the test number assigned to your app — picking the wrong WABA gets you a token that won't work against your test number.
2. Copy the generated token into `.env` as `WHATSAPP_ACCESS_TOKEN`, and the **Phone number ID** shown on the same page into `WHATSAPP_PHONE_NUMBER_ID`.
3. **Recipient management**: go to **Manage phone number list** to authorize a test recipient. Meta sends a mandatory OTP via WhatsApp to that device — enter it to verify.
4. **Test send**: send a standard template (e.g. "Order Confirmation") to the verified number from the dashboard. Check delivery status in the **Events** log in the UI.
5. **Token expiry — tighter than commonly assumed**: per Meta's Access Token Debugger, tokens generated this way expire roughly **1 hour** after generation, not 24h. Re-generate from the same **Generate Token** button when it lapses during dev — don't be surprised if a token that worked yesterday is dead today.

### 3. Set your own verify token
Pick any string (this project uses `chinook_verify_123`) and put it in `.env` as `WHATSAPP_VERIFY_TOKEN`. Meta doesn't generate this — you invent it, Meta just echoes it back during handshake to prove you own the endpoint.

### 4. Stand up the webhook + tunnel
Follow Part 2, steps 1-4 below to get `uvicorn` + `ngrok` running and get a public HTTPS URL.

### 5. Register the webhook with Meta
1. App dashboard → **WhatsApp → Configuration**.
2. **Callback URL**: `https://<your-ngrok-url>/webhook`
3. **Verify token**: whatever you set in step 3 above.
4. Click **Verify and save** — Meta calls your `GET /webhook` immediately; it only succeeds if uvicorn+ngrok are already running and `WHATSAPP_VERIFY_TOKEN` matches.
5. Under the same Configuration page, **Webhook fields** → subscribe to **`messages`** (this is what makes Meta actually push incoming chats to you, not just delivery/status events).

### 6. Send a test message through your own webhook
Different from step 2's dashboard "Try it out" test — this one confirms your actual FastAPI app, not just Meta's sandbox. From your verified recipient number, message the test number shown in API Setup. Confirm it reaches your uvicorn logs and you get a reply back. If the token from step 2 has expired (>1h old), regenerate it first.

### 7. Getting a permanent access token (skip for pure dev/testing)
The ~1h sandbox token is fine for validating logic but impractical for anything longer-running:
1. Requires **Business Verification** for the Business Portfolio (Meta Business Suite → Business Settings → Security Center) — takes real docs (business registration, etc.) and review time, not instant.
2. Once verified, create a **System User** (Business Settings → Users → System Users), assign it the WhatsApp app with full control, generate a token from there with no expiry (or long-lived).
3. Swap that into `.env`'s `WHATSAPP_ACCESS_TOKEN` — no code changes needed either way.

## Common Challenges

- **Facebook account must already exist, not freshly created.** Meta flags brand-new accounts for restrictions/extra verification on developer/business features — use an established personal account for the app owner, not one you just signed up.
- **Code changes require restarting uvicorn.** `uvicorn app.whatsapp_webhook:app --port 8000` doesn't hot-reload by default — edit `whatsapp_webhook.py` or anything it imports (`pipeline.py`, `config.py`, etc.), kill Terminal A, restart it, or your changes silently don't apply.
- **Both ngrok and uvicorn must be running at the same time.** Two separate terminals (Part 2, steps 4A/4B) — either one down and the whole chain breaks: ngrok alone has nothing to forward to, uvicorn alone has no public URL for Meta to reach.
- **Temporary access tokens expire in 24h.** The dev-mode `WHATSAPP_ACCESS_TOKEN` from API Setup goes stale daily — generate a fresh one from the Meta dashboard and update `.env` (then restart Terminal A) whenever requests start failing with auth errors.

## Part 2: Restart Guide

Steps to get the project running again after a restart.

## 1. Start MySQL (if not already running)
```bash
brew services start mysql
```

## 2. Start your LLM backend

- **LMStudio**: open the app, load your model, start the local server. Confirm `.env`'s `LLM_PROVIDER` and matching `LMSTUDIO_*`/`GEMINI_*` values are set correctly.
- **Gemini**: nothing to start — just make sure `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` are set in `.env`.

## 3. Start the Streamlit chat UI (optional — for browser testing)
```bash
.venv/bin/streamlit run app/main.py
```

## 4. Start the WhatsApp webhook (only if testing WhatsApp)

Two terminals, both must stay open:

**Terminal A — webhook server:**
```bash
.venv/bin/uvicorn app.whatsapp_webhook:app --port 8000
```

**Terminal B — ngrok tunnel:**
```bash
ngrok http 8000
```
Copy the `Forwarding` URL it prints (`https://xxxx.ngrok-free.dev`).

**If the ngrok URL changed** (it rotates every restart on the free plan):
1. Go to [developers.facebook.com](https://developers.facebook.com) → your app → WhatsApp → Configuration.
2. Update **Callback URL** to `https://<new-ngrok-url>/webhook`.
3. **Verify token** stays the same: `chinook_verify_123` (from `.env`'s `WHATSAPP_VERIFY_TOKEN`).
4. Click "Verify and save".

**If more than ~24h passed** since you last generated it, `WHATSAPP_ACCESS_TOKEN` in `.env` will have expired (Meta dev-mode temporary token). Generate a new one from the Meta dashboard and update `.env`, then restart Terminal A.

## 5. Sanity check before relying on it
```bash
curl -s http://127.0.0.1:4040/api/tunnels   # confirms ngrok is actually forwarding
```
If this returns nothing/connection refused, ngrok isn't really running even if its terminal window looks fine — restart it.

## Quick reference: what needs to be running for what

| You want to test... | Needs running |
|---|---|
| Streamlit chat in browser | MySQL + LLM backend + `streamlit run app/main.py` |
| WhatsApp | MySQL + LLM backend + uvicorn (Terminal A) + ngrok (Terminal B) |
| Quick CLI question | MySQL + LLM backend only (no server needed, see README.md section 7) |
