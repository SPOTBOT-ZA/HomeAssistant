# Roadmap

Ordered roughly by value/effort. v1 = core status+control (shipped by this
skeleton).

## 1. Webhook push → `cloud_push`

The biggest UX upgrade: firmware ≥ 374 devices can POST
detection/panic/heartbeat events (with `image_url`) to a configured URL, and
the integration can **self-register** its webhook at setup via
`POST /devices/{serial}/integrations`
`{integration: "webhook", action: "enable", webhook_url, auth_header,
auth_value}`.

Design notes (from the SPOTBOT webhook guide):

- One POST per detection *frame* — expect bursts (a dozen over minutes,
  two in the same second). Dedupe on `image_url`, coalesce per
  `serial + camera_nr` over 30–60 s into one HA event.
- Heartbeat is ~hourly, best-effort: mark offline only after **≥3
  consecutive missed** heartbeats; keep presence polling as fallback.
- No retries, 10 s timeout, any 2xx acknowledges.
- Fire `spotbot_detection` / `spotbot_panic` HA events; feed `image_url`
  into an `image` entity ("last detection").

Blockers: HA must be externally reachable (`webhook` component +
cloud/nabu-casa webhook URL support); **serial-format mismatch** — webhook
payloads carry a 13-digit serial while the REST API uses `S…_…` (looks like
the same digits with `S`/`_` stripped; verify on a live device); client epm
needs bit 6 (integrations).

## 2. Camera snapshots

`camera` entity per SpotBot camera: `GET /devices/{serial}/cameras/{n}/snapshot`
returns `{success, image}` (base64 JPEG, 15 s route). Requires epm bit 2.
Keep requests rare (each snapshot is a device round-trip): serve on demand
with a minimum interval, no preload.

## 3. Outputs / relays

`GET /outputs` → `{relay_id, output_name, trigger_time, trigger_cams}`;
`POST /outputs {action: "trigger", output_nr}` fires a relay → HA `button`
(momentary, `trigger_time` based) or `switch`. Requires epm bit 5.

## 4. Message / detection history

No REST endpoint exists today. Server work: expose the legacy
`get_messages_for_spotbots` (takes `sb_id`, `serials`, `last_NR`) as a
messaging-group route (bit 7). Then: "last detection" sensor with image +
class attributes without webhooks.

## 5. Per-camera snooze control + auto-snooze

**State: done.** `cam_status[].snooze` and `snoozed_until` are surfaced as a
per-camera `binary_sensor` "{camera} snoozed" (diagnostic), with
`snoozed_until` as an attribute. That fills the gap the device-wide Snooze
switch only pretended to fill, since `status.snooze` is `"false"` on every
device observed even while cameras are snoozed.

A timestamp sensor is still possible but needs care: `snoozed_until` is a
wall-clock `"HH:MM"` with no date, so a snooze started before midnight would
be dated a day early unless the rollover is handled.

**Control.** Routes exist (`snooze|unsnooze/{cam_nr}`, `POST /auto_snooze`).
Per-camera snooze should follow the device-wide one and be a **button pair**
rather than a switch, for the same reason: the device expires it by itself.
Auto-snooze thresholds are genuine settings, so `number`/`select` fits there.
A `number` for snooze duration would also expose the route's `time` field,
which a button cannot carry — presses currently use the server's default
hour.

## 6. Deployment picker

Replace the fixed `DEFAULT_APP_FOLDER` with
`application_credentials.async_get_auth_implementation()` returning a
per-deployment `AbstractOAuth2Implementation`. Entries already store
`base_url`, so no migration. Only worth it if non-NEO deployments must be
selectable at runtime.

## 7. PKCE → public client

Server-side PKCE at `/authorize`/`/token`, then flip
`sb_client_home_assistant` to `is_public = 1` and drop the client secret —
removes the secret-distribution problem entirely (HA supports
`LocalOAuth2ImplementationWithPkce`).

## 8. MQTT over WSS (exploratory)

`wss://signal.spotbot-evo.co.za/mqtt` (user = `sb_id`, password = JWT) has
retained presence/status topics — would eliminate polling. Needs
reconnect-on-token-refresh and confirmation of broker ACLs for third-party
clients.
