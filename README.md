# SpotBot for Home Assistant

Home Assistant custom integration for [SpotBot](https://spotbot.co.za)
AI-detection camera systems: control detection and armed response per camera,
snooze and mute your SpotBots, and watch device/camera connectivity — all from
Home Assistant.

- **Auth**: OAuth2 (phone number + one-time PIN — no extra password)
- **Transport**: SpotBot cloud REST API (`cloud_polling`, 2-minute interval)
- **Requires**: Home Assistant ≥ 2026.3.0, a SpotBot account

> ⚠️ Work in progress. The backing API deployment (`SPOTBOT_APP_NEO`) is not
> live yet; nothing here is end-to-end tested against real devices. See the
> `TODO(live-verify)` markers in `custom_components/spotbot/api.py`.

## Entities (v1)

| Entity | Type | Per |
|---|---|---|
| Detection | switch | camera |
| Armed response | switch | camera |
| Snooze | switch | device |
| Speaker mute | switch | device |
| Online | binary_sensor (diagnostic) | device |
| Camera connectivity | binary_sensor (diagnostic) | camera |
| Panic | button (**disabled by default** — triggers a real armed response) | device |

## Installation

Short version: install via HACS (custom repository) or copy
`custom_components/spotbot/` into your config, add the SpotBot application
credentials, then add the integration and sign in with your phone number.
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
(`SPOTBOT/SPOTBOT_HOMEASSISTANT`, also vendored as the `HOMEASSISTANT/`
submodule of `SPOTBOT_APP`) and mirrored to public GitHub for HACS and CI.
GitHub Actions run **on the mirror only**: hassfest + HACS validation, pytest,
and automatic GitHub Releases from `v*` tags.

## License

[MIT](LICENSE)
