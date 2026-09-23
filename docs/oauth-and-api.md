# OAuth & API reference (Home Assistant context)

Everything the integration needs to know about the SpotBot OAuth server and
REST gateway, distilled from the server source (`SPOTBOT_API` repo:
`oauth/index.php`, `index.php`, `endpoint_groups.php`). Live references:

- `<base>/oauth/version` — OAuth server version probe (no auth)
- `<base>/public/swagger.php` — public Swagger UI
- `<base>/endpoint_groups.php` — rendered endpoint-mask reference
- `<base>/` — API root/version probe (no auth)

`<base>` = `https://www.spotbot-evo.co.za/SPOTBOT_APP_NEO/API` for this
integration (see `const.py`).

## OAuth server

| Endpoint | Purpose |
|---|---|
| `GET <base>/oauth/authorize` | Start the flow. Renders the SpotBot login (phone → OTP). `state` is **mandatory**, `response_type` must be `code`. |
| `POST <base>/oauth/token` | `authorization_code` and `refresh_token` grants. Body **must** be `application/x-www-form-urlencoded`. |
| `GET <base>/oauth/userinfo` | Bearer-authenticated identity: `{sb_id, name, surname, cellnumber, email, permissions}`. Cheap token-validity probe. |
| `POST <base>/oauth/revoke` | Revoke a token. |

Facts that shape the client code:

- **No PKCE.** Hence a *confidential* client; users supply client_id +
  client_secret through HA's Application Credentials UI.
- **No discovery document, no JWKS.** URLs are hardcoded constants.
- **No consent screen, no password.** Login is phone number + 4-digit OTP
  (SMS/push), with an inline account-creation step for unknown numbers.
- **Tokens are HS256 JWTs** signed with a per-client key. Access token TTL is
  configured per client (3600 s requested for the HA client; server default
  is 600 s). Claims include `sub` (sb_id), `cell`, `cid` (client id), `epm`
  (endpoint mask), `dev` (OAuth device id).
- **Refresh tokens live 30 days and are NOT rotated** — the same value stays
  valid; only its expiry slides forward on use. (Server README claims
  rotation; the code deliberately does not rotate.) A refresh fails with
  `invalid_grant` + a `reason` field (`not_found`/`expired`/`revoked`) if the
  `ha-…` device row was deleted from the account — that surfaces in HA as a
  reauth prompt.
- **Authorization codes** are single-use and expire after 10 minutes.
- The server validates `redirect_uri` against the client's stored patterns at
  `/authorize` (exact match works; `*` wildcards supported) but only compares
  **scheme+host** at `/token`.

### Gotchas (learned from the source)

1. Any redirect URI containing `spotbot-evo.co.za` triggers a special
   "token bridge" page instead of the standard `?code=…&state=…` redirect.
   `https://my.home-assistant.io/redirect/oauth` is safe; never register a
   spotbot-evo.co.za redirect on the HA client.
2. The OAuth URLs must contain the `/SPOTBOT_APP*/` path segment — the server
   derives its deployment folder from it and silently falls back to another
   deployment when the segment is missing.
3. `state` is echoed back but **not** validated server-side on return; Home
   Assistant's OAuth helper validates it client-side (it encodes the flow id).

## REST gateway (`<base>/api/v2`)

Authentication: `Authorization: Bearer <JWT>` on every route. Authorization:
the JWT's `epm` bitmask (below). Errors: RFC 7807 `application/problem+json`
(`{type, title, status, detail}`).

### Status-code quirks the client absorbs (`api.py`)

| Code | Meaning | Client behavior |
|---|---|---|
| 401 | Missing/malformed Authorization header | `SpotBotAuthError` → reauth |
| **403** | **Three** different things (see below) | Told apart by reading the problem+json body; `/oauth/userinfo` is only the fallback when the body says nothing |
| **504** | Device did not answer over MQTT — i.e. **device offline** | `SpotBotDeviceOfflineError`; treated as unavailability, never as a setup/update failure |
| 404 `no_presence` | No retained presence message for the serial | Presence = unknown/offline |
| 502 `mqtt_*` / `rpc_error` | Broker or device-side errors | `SpotBotApiError`, logged, retried next cycle |

#### The three meanings of 403

The gateway overloads 403, but its `problem+json` body distinguishes them, so
`_classify_403` reads that first:

| `type` | `title` | Means | Client |
|---|---|---|---|
| `…/rpc_error` | `Device returned an error` | The **device or gateway** refused the RPC (`index.php` maps an RPC-level 401/403 onto HTTP 403). Per-device, and seen to be transient | `SpotBotDeviceRefusedError`, carrying the device's own detail |
| `…/forbidden` | `Endpoint not available` | The OAuth client's endpoint mask really does deny the route | `SpotBotPermissionError` |
| `…/forbidden` | `Invalid or expired token` | Bad JWT | `SpotBotAuthError` → reauth |

Only when the body carries none of these does the client fall back to probing
`/oauth/userinfo`, which succeeds for any valid token and so separates a live
token from a dead one without side effects.

This matters more than it looks: treating every 403 as an endpoint-mask denial
sends people to the management console to widen a mask that is already
correct. That happened in testing, against a client whose `epm` was `0x0803`
the whole time.

### Payload quirks

- `status.cam_status` may arrive as a **JSON-encoded string** instead of a
  list — `SpotBotStatus.from_json` coerces it.
- Field typing is loose, and confirmed against live payloads: `onoff` is `0`/`1`
  as a number; `ar_onoff` is `0`/`1` as a number **or the string `"NA"`**;
  `snooze` and `Mute_status` are the strings `"true"`/`"false"`. Booleans go
  through `_as_bool`, which handles all of those — but `"NA"` is *not* a
  boolean: it means armed response does not exist on that camera, so
  `_is_applicable` separates it and no entity is created. Flattening it to
  `False` produces a switch that reads *off* and silently no-ops.
- `speaker_mute` takes `{"todo": "1"|"0"}` — `"1"` mutes. The device ignores
  keys it does not know and falls through to **unmuting**, so a wrong key
  fails silently in the "unmute" direction and mute can never engage. Only
  `swagger-internal.php` documents this route; the public spec omits it.
- `conn_status` is a **fault code, not a boolean**: `0` "Fine", `1` warning,
  `2` error/video off, anything else unknown. Only `0` means connected, and
  it is the value a healthy camera reports — the apps hide the indicator for
  `0` and draw something only for the rest (`getConnectionStatusIcon` in the
  legacy JS, `CameraStatusGrid` in the PWA). Running it through `_as_bool`
  inverts the sensor and reports every healthy camera as disconnected, which
  is what this client did until it was caught: the field reading `0`
  everywhere looked like a gateway that was not populating it, and was
  actually every camera saying it was fine.
- `/presence` returns a **flattened** object `{serial, online, ts, fw,
  presence}` (the Swagger spec wrongly documents a `data` envelope; the code
  wins).
- Identity is injected server-side from the JWT — the client never sends
  `sb_id`, `device_id`, usernames, etc.
- Routes used in v1 (all confirmed against the server route table):
  `GET /account/devices`, `GET /devices/{serial}/status`,
  `GET /devices/{serial}/presence`, `POST /devices/{serial}/on|off/{cam|all}`,
  `POST /devices/{serial}/ar_on|ar_off/{cam|all}`,
  `POST /devices/{serial}/snooze|unsnooze/{cam|all}`,
  `POST /devices/{serial}/speaker_mute`, `POST /devices/{serial}/panic`.
- **There is no message/image history endpoint** in the REST API today (the
  legacy `get_messages_for_spotbots` function exists server-side but is not
  exposed) — see [roadmap](roadmap.md).

## Endpoint mask (`epm`) — the real authorization model

OAuth `scope` is accepted and ignored. Authorization is a 16-bit per-client
bitmask checked per route group:

| Bit | Group | Used by this integration |
|---|---|---|
| 0 | status | ✔ status, presence |
| 1 | control | ✔ on/off, ar, snooze, mute, panic |
| 2 | cameras | roadmap (snapshots) |
| 5 | outputs | roadmap (relays) |
| 6 | integrations | roadmap (webhook self-registration) |
| 11 | account | ✔ device list |

The HA client's mask is **0x0803** (bits 0, 1, 11 — the same as the server's
`google_home` preset). The mask is baked into the JWT at mint time, so after
widening it in the management console a token refresh is needed before the
new groups work.
