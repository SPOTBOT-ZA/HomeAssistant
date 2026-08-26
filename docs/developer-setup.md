# Developer setup

## Source of truth & mirror

Development happens on the self-hosted Gitea:
`http://thinkstation.local:3000/SPOTBOT/SPOTBOT_HOMEASSISTANT` (also checked
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

> The API is not yet live on the NEO deployment, so end-to-end testing is
> currently blocked; offline checks below all work.

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

Quickest loop: a HA core dev container or a plain venv install
(`pip install homeassistant`), then symlink or copy
`custom_components/spotbot` into its config dir, add Application Credentials
for your dev client, and add the integration. Watch the log for the
`TODO(live-verify)` items in `api.py` — the exact value vocabulary of
`Mute_status`, `onoff`/`ar_onoff` and the `/speaker_mute` POST body must be
confirmed against a live device before release.

## Release procedure

1. Bump `version` in `custom_components/spotbot/manifest.json`.
2. Commit on `main`, tag `vX.Y.Z`, push branch + tag to Gitea.
3. The push-mirror syncs to GitHub; the `release.yml` workflow turns the tag
   into a GitHub Release (which is what HACS versions from).
