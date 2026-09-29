# Registration: HACS, brands, and the path to core

Verified against the developer/HACS docs as of August 2026.

## Stage 0 — installable today (custom repository)

Nothing to register: any user can add the public GitHub mirror as a HACS
custom repository (HACS → ⋮ → Custom repositories → paste URL, type
*Integration*). Requirements already met by this repo: one integration per
repo under `ROOT/custom_components/spotbot/`, `hacs.json` with `name`, a
README, and (for versioned installs) GitHub Releases.

## Stage 1 — HACS default store

Goal: users find "SpotBot" in HACS search without adding a custom repo.

Checklist (from hacs.xyz/docs/publish):

- [x] Public GitHub repo with **description**, **topics**, and **Issues
      enabled** — `SPOTBOT-ZA/HomeAssistant`, public 2026-09-29
- [x] `hacs.json` with at least `name`
- [x] README with usage docs
- [x] **At least one GitHub Release** (not just a tag) — `v0.1.0`, created by
      `release.yml` from the tag
- [x] **HACS Action** and **hassfest** pass without errors — 9/9 green on the
      mirror. They only pass on a *public* repo: while it was private the
      action could not fetch files, and `integration_manifest` and `hacsjson`
      failed with "Got None" although both files were fine.
- [x] Brand icon — inline `brand/`; see Stage 2, nothing to submit
- [ ] Submit a PR to `https://github.com/hacs/default` adding the repo URL to
      the `integration` file, **alphabetically sorted**, from a branch off
      `master`, **submitted by the repo owner or a major contributor's
      personal account** (not an org account)

Expect review to take **months**; the integration stays installable as a
custom repository meanwhile. Alpha/beta-stage integrations are excluded —
submit once v1 is stable.

## Stage 2 — home-assistant/brands — **nothing to do, do not submit**

Icons are already handled. The integration ships them inline —
`custom_components/spotbot/brand/icon.png` (256×256) and `icon@2x.png`
(512×512), rendered from `blueicon.svg` — and Home Assistant serves those
through the brands proxy from **2026.3.0** onward, which is the floor
`hacs.json` sets. Every user who can run this integration gets the icon.

**`home-assistant/brands` no longer accepts custom-integration icons.** A PR
there is closed automatically within seconds:

> we no longer accept brand icons for custom integrations in this
> repository. Starting with Home Assistant 2026.3.0, custom integrations can
> provide their own brand icons directly

See the [brands proxy API
announcement](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api)
(2026-02-24).

This section previously recommended submitting anyway, "so users on older HA
see the logo". That was wrong twice over: the submission is refused, and
`hacs.json` requires 2026.3.0, so there are no older users to serve. It was
acted on — [home-assistant/brands#11251](https://github.com/home-assistant/brands/pull/11251),
opened and bot-closed on 2026-09-29 — which is why it is spelled out here
rather than quietly deleted.

The only thing to keep in mind: the icons must stay where they are, and the
folder name `brand/` and the manifest `domain` (`spotbot`) must keep
matching.

## Stage 3 — core integration (long-term option)

Submitting to `home-assistant/core` requires substantially more:

- The API client must move out of the integration into a **published PyPI
  library** (source distribution + its own issue tracker); the manifest then
  lists it in `requirements`.
- Minimum **Bronze** quality tier: full test coverage of `config_flow.py`,
  `runtime_data`, unique config entry, appropriate polling, has_entity_name —
  the skeleton already follows these patterns.
- Brands assets move to `core_integrations/`, plus a documentation PR to
  `home-assistant.io`.
- OAuth for core: either keep user-supplied Application Credentials, or
  arrange **Cloud Account Linking** with Nabu Casa (they host the credentials;
  seamless UX — requires coordination between SpotBot and Nabu Casa).
- Note: `version` must be *removed* from the manifest for core.
