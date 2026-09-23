# Architecture

How the SpotBot Home Assistant integration talks to the SpotBot platform, and
why it is shaped the way it is.

## The moving parts

```
┌────────────────────┐   OAuth2 (authorization code)   ┌──────────────────────────────┐
│   Home Assistant   │────────────────────────────────▶│ SpotBot OAuth server         │
│                    │◀────────────────────────────────│ <base>/oauth/*               │
│  custom_components │        access + refresh JWT     └──────────────────────────────┘
│      /spotbot      │
│                    │   REST (Bearer JWT)             ┌──────────────────────────────┐
│  DataUpdate-       │────────────────────────────────▶│ SpotBot REST gateway         │
│  Coordinator       │◀────────────────────────────────│ <base>/api/v2/*              │
└────────────────────┘                                 │  (HTTP → MQTT RPC bridge)    │
                                                       └──────────────┬───────────────┘
                                                                      │ MQTT (signal.spotbot-evo.co.za:1883)
                                                                      ▼
                                                       ┌──────────────────────────────┐
                                                       │  SpotBot device (per serial) │
                                                       │  cameras, speaker, relays    │
                                                       └──────────────────────────────┘
```

`<base>` is `https://www.spotbot-evo.co.za/<APP_FOLDER>/API`. The Home
Assistant integration is served by the **SPOTBOT_APP_NEO** deployment
(`const.DEFAULT_APP_FOLDER`).

Two properties of the REST gateway drive every design decision here:

1. **It is not a database API.** Each `/api/v2/devices/{serial}/...` request
   is relayed to the physical device over MQTT and blocks server-side until
   the device answers or the route times out (8 s typical). A request to an
   offline device burns the full timeout and returns **504** — that is the
   *normal* "device offline" signal, not an error.
2. **Every request parks a PHP worker** for its duration. Aggressive polling
   hurts the whole platform, so the integration polls at a 120 s interval and
   throttles per-device fan-out with a small semaphore.

## Polling model (`coordinator.py`)

Every refresh cycle:

1. `GET /account/devices` — one call, lists all SpotBots on the account.
2. Per device, throttled to 2 concurrent requests:
   - `GET /devices/{serial}/presence` — cheap (3 s route, reads the retained
     MQTT presence message; no device round-trip).
   - Only if the device is **online**: `GET /devices/{serial}/status` — full
     state including `cam_status[]`. Skipping offline devices avoids a
     guaranteed 8 s timeout + 504 per offline device per cycle.
3. The last known status is kept while a device is offline, so entity state
   doesn't flap to unknown during outages.

Commands (`switch`/`button` presses) call the corresponding POST route and
then request a coordinator refresh so state converges.

## Endpoint → entity map (v1)

| API route | Entity | Notes |
|---|---|---|
| `GET /account/devices` | one HA *device* per `Serial` | name = `Bot_title` or `Name` |
| `GET /devices/{s}/presence` → `online` | `binary_sensor` (connectivity, diagnostic) | reports **off** rather than unavailable when down |
| `GET /devices/{s}/status` → `cam_status[].onoff` | `switch` "{camera} detection" per camera | `POST /on|off/{cam_nr}` |
| `status` → `cam_status[].ar_onoff` | `switch` "{camera} armed response" per camera | `POST /ar_on|ar_off/{cam_nr}`. **`"NA"` means the camera has no armed response — no entity is created.** The API still accepts arm/disarm for such a camera and returns success while the device ignores it, so the value is the only way to know |
| `status` → `cam_status[].conn_status` | `binary_sensor` "{camera} connectivity" (diagnostic) | **A fault code, not a flag**: `0` "Fine", `1` warning, `2` error/video off, anything else unknown. Only `0` is connected. The apps hide the indicator entirely for `0` and draw something only for the rest (`legacyStuff/js-functions.js` → `getConnectionStatusIcon`, and the PWA's `CameraStatusGrid`). The raw code rides along as a `conn_status` attribute, since warning and error are different problems the binary sensor flattens together |
| — | `button` "Snooze" / "Unsnooze" per device | `POST /snooze|unsnooze/all`. Buttons, not a switch: snooze is timed and the device expires it by itself. A press uses the server's default hour — the route's `time` field has no equivalent on a button |
| `status` → `cam_status[].snooze`, `snoozed_until` | `binary_sensor` "{camera} snoozed" (diagnostic) | The **per-camera** snooze state, and the only one that is real: the device-level `status.snooze` is `"false"` on every device observed, even with cameras snoozed, so the old device-wide Snooze switch could never report the truth. Read-only — the Snooze/Unsnooze buttons act. `snoozed_until` is a wall-clock `"HH:MM"` with no date, so it is an attribute rather than a guessed timestamp |
| `status` → `Mute_status` | `switch` "Speaker mute" per device | `POST /speaker_mute` |
| — | `button` "Panic" per device | `POST /panic`; **disabled by default** (it triggers a real armed-response chain) |

All other entities go through the normal availability rule: unavailable while
the device is offline.

## Why `cloud_polling` (for now)

The platform has push channels, but none are usable in v1:

- **Generic Webhook** (firmware ≥ 374): the device POSTs
  detection/panic/heartbeat events to a configurable URL. This is the planned
  path to `cloud_push` — Home Assistant can self-register its webhook via
  `POST /devices/{serial}/integrations`. Blocked v1 by the serial-format
  mismatch (webhook payloads carry a 13-digit serial, the REST API uses the
  `S…_…` form) and by needing an externally reachable HA URL. See
  [roadmap](roadmap.md).
- **MQTT over WSS** (`wss://signal.spotbot-evo.co.za/mqtt`, username =
  `sb_id`, password = the JWT): retained presence/status topics would remove
  polling entirely, but the JWT-as-password expires hourly, forcing constant
  reconnects, and broker ACLs for third-party clients are unverified.
- **FCM**: mobile-app-only, not consumable by HA.

## Authorization model

There are no OAuth scopes (the server accepts and ignores `scope`). Access is
governed by the OAuth client's **endpoint mask** (`epm`), a 16-bit bitmask
baked into every JWT. The Home Assistant client uses `0x0803` = status (bit 0)
+ control (bit 1) + account (bit 11). Calling a route outside the mask returns
403. Widening the mask (e.g. adding cameras, bit 2) takes effect on the next
token refresh. See [oauth-and-api.md](oauth-and-api.md).
