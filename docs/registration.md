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

- [ ] Public GitHub repo with **description**, **topics**, and **Issues
      enabled**
- [ ] `hacs.json` with at least `name` ✔ (in repo)
- [ ] README with usage docs ✔
- [ ] **At least one GitHub Release** (not just a tag) — created by
      `release.yml` on tag push ✔ (mechanism in place)
- [ ] **HACS Action** and **hassfest** pass without errors
      (`.github/workflows/validate.yml` ✔ — must be green on the mirror)
- [ ] Brand icon available (inline `brand/` ✔, or home-assistant/brands —
      below)
- [ ] Submit a PR to `https://github.com/hacs/default` adding the repo URL to
      the `integration` file, **alphabetically sorted**, from a branch off
      `master`, **submitted by the repo owner or a major contributor's
      personal account** (not an org account)

Expect review to take **months**; the integration stays installable as a
custom repository meanwhile. Alpha/beta-stage integrations are excluded —
submit once v1 is stable.

## Stage 2 — home-assistant/brands

The integration ships its own icons inline
(`custom_components/spotbot/brand/icon.png` 256×256 + `icon@2x.png` 512×512,
rendered from `blueicon.svg`), which HA ≥ 2026.3 serves through the brands
proxy. A submission to `https://github.com/home-assistant/brands` is still
worthwhile so users on older HA (and some HACS UI surfaces) see the logo:

- PR adding `custom_integrations/spotbot/` containing `icon.png` (256×256)
  and `icon@2x.png` (512×512); optionally `logo.png`/`logo@2x.png`
  (landscape, shortest side ≥128/≥256 px) and `dark_*` variants.
- The folder name must exactly match the manifest `domain` (`spotbot`).

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
