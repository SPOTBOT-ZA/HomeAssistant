# Installation (end users)

Requirements: Home Assistant **2026.3.0 or newer**, a SpotBot account (phone
number), and the SpotBot application credentials (client ID + secret —
published in step 2 below).

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

## 2. Add application credentials

Home Assistant integrations cannot ship built-in OAuth credentials, so you
enter them once by hand. They are the same for every SpotBot user:

| Field | Value |
|---|---|
| Client ID | `sb_client_home_assistant` |
| Client secret | `c23a75477684575eb38c943b5cfbc3d849a68a0fcfe1c4d176076c37abcf09f2` |

1. In HA: **Settings → Devices & Services → ⋮ → Application Credentials →
   Add Application Credential**
2. Integration: *SpotBot*; paste the client ID and secret above.

The secret is deliberately low-value: it identifies the Home Assistant
integration, not you. Issuing a token still requires *your* phone number and
one-time PIN, and the client is limited to the status, control and account
endpoints.

## 3. Add the integration

1. **Settings → Devices & Services → Add Integration → SpotBot**
2. Your browser opens the SpotBot login page: enter your **phone number**,
   then the **one-time PIN** you receive (SMS or app push). There is no
   password — the OTP is the login.
3. You are redirected back via `my.home-assistant.io` and the account is
   linked. One config entry represents one SpotBot account; every SpotBot on
   the account appears as a device.

## What you get (v1)

Per SpotBot device:

- **Switches** — per-camera *detection* and *armed response*, device-wide
  *snooze*, *speaker mute*
- **Binary sensors** (diagnostic) — device *online*, per-camera *connectivity*
- **Button** — *Panic* (**disabled by default**; enable it consciously in the
  entity settings — it triggers a real armed-response chain)

State refreshes every 2 minutes. Commands apply immediately and re-sync.

## Troubleshooting

- **"Missing configuration" when adding the integration** — Application
  Credentials (step 2) haven't been added yet.
- **"Invalid client_id" on the SpotBot login page** — the client ID was
  mistyped; it is `sb_client_home_assistant` exactly.
- **Login page never redirects back** — the flow relies on
  [my.home-assistant.io](https://my.home-assistant.io). If you disabled the
  `my` integration, re-enable it (`default_config` includes it); a
  local-callback alternative is not supported in v1.
- **Re-authentication prompt** — your refresh token expired (30 days unused)
  or the `ha-…` device was removed from your SpotBot account (SpotBot app →
  signed-in devices). Sign in again; entities and history are preserved.
- **Everything unavailable** — check the device online sensor: when the
  SpotBot itself is offline (power/network), the cloud cannot reach it and
  all its entities go unavailable. This is expected.
