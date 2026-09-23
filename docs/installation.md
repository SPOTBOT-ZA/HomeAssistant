# Installation (end users)

Requirements: Home Assistant **2026.3.0 or newer** and a SpotBot account
(phone number). There is nothing to request from support — the integration
brings its own OAuth credentials.

## 1. Install the integration

### Via HACS (recommended)

Until the integration is accepted into the HACS default store, add it as a
custom repository:

1. HACS → three-dot menu (top right) → **Custom repositories**
2. Repository: `https://github.com/GITHUB-ORG-TODO/SPOTBOT_HOMEASSISTANT`
   — type **Integration** → **Add**
3. Search for "SpotBot" in HACS, install it, and restart Home Assistant.

### Manual

Copy `custom_components/spotbot/` from this repository into your Home
Assistant `config/custom_components/` directory and restart.

## 2. Add the integration

1. **Settings → Devices & Services → Add Integration → SpotBot**
2. Your browser opens the SpotBot login page: enter your **phone number**,
   then the **one-time PIN** you receive (SMS or app push). There is no
   password — the OTP is the login.
3. You are redirected back via `my.home-assistant.io` and the account is
   linked. One config entry represents one SpotBot account; every SpotBot on
   the account appears as a device.

There is no client ID or secret to enter: the integration registers its own
OAuth client the moment you click **Add Integration**. The credentials are
the same for every installation and are published in
[server-setup.md](server-setup.md) — the secret identifies the integration,
not you, and issuing a token still requires *your* phone number and one-time
PIN. To use your own SpotBot OAuth client instead, add it under **Settings →
Devices & Services → ⋮ → Application Credentials** before adding the
integration, and pick it when the flow asks which to use.

## What you get (v1)

Per SpotBot device:

- **Switches** — per-camera *detection* and *armed response*, device-wide
  *speaker mute*
- **Buttons** — *Snooze* and *Unsnooze*, device-wide. Snooze is a timed action
  the SpotBot expires by itself, so it is a button rather than a switch: a
  press pauses detection on every camera for an hour (the server's default),
  and Unsnooze resumes them early.
- **Binary sensors** (diagnostic) — device *online*, per-camera *connectivity*
  and *snoozed* (carrying the time the snooze runs until)
- **Button** — *Panic* (**disabled by default**; enable it consciously in the
  entity settings — it triggers a real armed-response chain)

Cameras without armed response get no armed-response switch. The SpotBot
reports those as `"NA"`, and the API accepts an arm/disarm command for them
and reports success while the device ignores it — so a switch there would
read *off* and do nothing.

State refreshes every 2 minutes. Commands apply immediately and re-sync.

## Troubleshooting

- **"Missing configuration" / "Missing credentials" when adding the
  integration** — the built-in client failed to register, which means a
  broken install rather than a missing step. Check the log, then reinstall.
- **"Invalid client_id" on the SpotBot login page** — the deployment this
  build points at has no `sb_client_home_assistant` client registered (see
  [server-setup.md](server-setup.md)), or you substituted your own client
  and mistyped its ID.
- **Login page never redirects back** — the flow relies on
  [my.home-assistant.io](https://my.home-assistant.io), which sends the
  browser to the instance URL *it* has stored for you. If that URL is not
  the one you actually reach Home Assistant on, the final hop lands nowhere
  and the flow appears to hang: open my.home-assistant.io and correct it.
  If you disabled the `my` integration, re-enable it (`default_config`
  includes it); a local-callback alternative is not supported in v1.
- **Re-authentication prompt** — your refresh token expired (30 days unused)
  or the `ha-…` device was removed from your SpotBot account (SpotBot app →
  signed-in devices). Sign in again; entities and history are preserved.
- **Everything unavailable** — check the device online sensor: when the
  SpotBot itself is offline (power/network), the cloud cannot reach it and
  all its entities go unavailable. This is expected.
