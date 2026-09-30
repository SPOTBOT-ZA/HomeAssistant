# Developer setup

## Source of truth & mirror

Development happens on the self-hosted Gitea:
`http://thinkstation.local:3000/SPOTBOT/HomeAssistant` (also checked
out as the `HOMEASSISTANT/` submodule of `SPOTBOT_APP`). A public GitHub
mirror serves HACS and runs CI — see [mirroring.md](mirroring.md). Never
commit anything secret: everything on `main` becomes public via the mirror.

## Targeting a deployment

All OAuth/API URLs derive from one constant:
`custom_components/spotbot/const.py` → `DEFAULT_APP_FOLDER`
(currently `SPOTBOT_APP_NEO`). To test against another deployment
(`SPOTBOT_APP_PAUL`, …):

1. Edit `DEFAULT_APP_FOLDER`.
2. Register the OAuth client in **that** deployment's management console
   (per-deployment databases → per-deployment clients/keys), per
   [server-setup.md](server-setup.md).

> NEO is live and the integration has been tested end to end against it.
> Note the OAuth client is per deployment: `sb_client_home_assistant` exists
> on NEO, so pointing `DEFAULT_APP_FOLDER` elsewhere means registering it
> there too, and updating `OAUTH_CLIENT_ID`/`OAUTH_CLIENT_SECRET` in
> `const.py` to match that deployment's client.

## Offline checks

```bash
python3 -m compileall custom_components          # syntax
python3 -m json.tool custom_components/spotbot/manifest.json
python3 -m json.tool custom_components/spotbot/strings.json
```

## Tests

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt             # pulls in homeassistant itself
pytest
```

The suite uses `pytest-homeassistant-custom-component`: the config-flow test
drives the full OAuth dance against mocked HTTP endpoints; the init tests
exercise setup, the 504-offline path, unload, and the cam_status-as-string
coercion. Fixture JSONs in `tests/fixtures/` mirror real API payload shapes —
when a live payload disagrees, fix the fixture *and* the parser together.

Structure validation (hassfest + HACS action) runs in CI on the GitHub
mirror (`.github/workflows/validate.yml`).

## Running in a dev Home Assistant

Quickest loop: the official container with the component bind-mounted
straight out of this repo, so an edit is one restart away —

```bash
docker run -d --name homeassistant --restart unless-stopped \
  -p 8123:8123 -e TZ=Africa/Johannesburg \
  -v <config-dir>:/config \
  -v "$PWD/custom_components/spotbot:/config/custom_components/spotbot" \
  ghcr.io/home-assistant/home-assistant:stable
docker restart homeassistant     # after every edit
```

A HA core dev container or a venv install (`pip install homeassistant`) with
the component symlinked in works the same way. Nothing to set up on the
Application Credentials side — the integration registers its own client.

Python caches bytecode into `custom_components/spotbot/__pycache__` as root
from inside the container; clear it with
`docker exec homeassistant rm -rf /config/custom_components/spotbot/__pycache__`
rather than `sudo` on the host.

The three `TODO(live-verify)` items that used to sit in `api.py` are all
resolved against live devices — `Mute_status` and `snooze` are the strings
`"true"`/`"false"`, `onoff` is a number, `ar_onoff` is a number or `"NA"`,
and `/speaker_mute` takes `{"todo": "1"|"0"}`. See
[oauth-and-api.md](oauth-and-api.md) for the full vocabulary; if a live
payload ever disagrees, fix the fixture *and* the parser together.

## Release procedure

1. Bump `version` in `custom_components/spotbot/manifest.json`.
2. Commit on `main`, tag `vX.Y.Z`, push branch + tag to Gitea.
3. The push-mirror syncs to GitHub; the `release.yml` workflow turns the tag
   into a GitHub Release (which is what HACS versions from).
