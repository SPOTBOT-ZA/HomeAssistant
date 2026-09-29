# SpotBot for Home Assistant

Home Assistant custom integration for [SpotBot](https://spotbot.co.za)
AI-detection camera systems: control detection and armed response per camera,
snooze and mute your SpotBots, and watch device/camera connectivity — all from
Home Assistant.

- **Auth**: OAuth2 (phone number + one-time PIN — no extra password)
- **Transport**: SpotBot cloud REST API (`cloud_polling`, 2-minute interval)
- **Requires**: Home Assistant ≥ 2026.3.0, a SpotBot account

> Verified end to end against the `SPOTBOT_APP_NEO` deployment on a live
> account — sign-in, polling and every control below driven against real
> devices. Still v1: see [roadmap](docs/roadmap.md) for what is not here yet.

## Entities (v1)

| Entity | Type | Per |
|---|---|---|
| Detection | switch | camera |
| Armed response | switch | camera — only where the device provides it (see below) |
| Speaker mute | switch | device |
| Snooze / Unsnooze | button | device |
| Online | binary_sensor (diagnostic) | device |
| Camera connectivity | binary_sensor (diagnostic) | camera |
| Snoozed | binary_sensor (diagnostic), with `snoozed_until` | camera |
| Panic | button (**disabled by default** — triggers a real armed response) | device |

Two of those need a word of explanation:

- **Snooze is a button, not a switch.** It is a timed action the device
  expires by itself, so there is no state for Home Assistant to hold and
  nothing to switch back off. A press snoozes every camera on the device for
  the server's default of one hour; Unsnooze resumes them.
- **Armed response only appears where the camera has it.** A camera that
  reports `ar_onoff: "NA"` is not provisioned for armed response and gets no
  entity — it would otherwise read *off* and silently do nothing, since the
  API accepts the command and returns success while the device ignores it.

## The SpotBot card

The integration ships a Lovelace card shaped like the card in the SpotBot
app: a header that follows the device's reachability, numbered camera
indicators coloured by detection, a second row for armed response, the
snoozed cameras with the time each snooze runs out, and the snooze controls.
Camera indicators are clickable — they toggle that camera.

It is served by the integration itself, so there is nothing to install or
register. Add a Manual card and give it the device slug:

```yaml
type: custom:spotbot-card
device: spotbot_bosplaas
```

The slug is the entity-id prefix the integration uses for that SpotBot —
`binary_sensor.spotbot_bosplaas_connectivity` means `spotbot_bosplaas`.

Cameras reporting a connectivity fault show a warning or no-video icon in
place of their number, as the apps do. There is no last-detection preview:
the REST API exposes no messages endpoint, so Home Assistant never sees
them — see [roadmap](docs/roadmap.md).

## Installation

Short version: install via HACS (custom repository) or copy
`custom_components/spotbot/` into your config, then add the integration and
sign in with your phone number. There is no client ID or secret to enter —
the integration registers its own OAuth client.
**Full walkthrough: [docs/installation.md](docs/installation.md).**

## Documentation

| Doc | What's in it |
|---|---|
| [architecture](docs/architecture.md) | How HA ⇄ OAuth ⇄ REST-gateway ⇄ MQTT ⇄ device fits together; polling model; endpoint→entity map |
| [oauth-and-api](docs/oauth-and-api.md) | The SpotBot OAuth server and REST API from an HA perspective, incl. every quirk the client absorbs |
| [server-setup](docs/server-setup.md) | Registering the `sb_client_home_assistant` OAuth client (management console recipe) |
| [installation](docs/installation.md) | End-user install + troubleshooting |
| [developer-setup](docs/developer-setup.md) | Dev environment, tests, targeting other deployments, release procedure |
| [registration](docs/registration.md) | HACS default store, home-assistant/brands, path to core |
| [mirroring](docs/mirroring.md) | Gitea → GitHub push-mirror that feeds HACS + CI |
| [roadmap](docs/roadmap.md) | Webhook push (`cloud_push`), cameras, outputs, history, PKCE |

## Repository layout

This repo is developed on a self-hosted Gitea
(`SPOTBOT/HomeAssistant`, also vendored as the `HOMEASSISTANT/`
submodule of `SPOTBOT_APP`) and mirrored to public GitHub for HACS and CI.
GitHub Actions run **on the mirror only**: hassfest + HACS validation, pytest,
and automatic GitHub Releases from `v*` tags.

## License

[MIT](LICENSE)
