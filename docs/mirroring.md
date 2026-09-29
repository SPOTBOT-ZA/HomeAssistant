# Gitea → GitHub mirroring

HACS only installs from **public GitHub repositories**, and GitHub Actions
(hassfest/HACS validation, release creation) only run on GitHub. The Gitea
repo stays the source of truth; a push-mirror keeps a public GitHub clone in
sync.

> Done: the mirror is [SPOTBOT-ZA/HomeAssistant](https://github.com/SPOTBOT-ZA/HomeAssistant).
> Note the repo name is **`HomeAssistant`**, not `SPOTBOT_HOMEASSISTANT` as
> this doc originally planned. It must be **public** for HACS to install from
> it; the org's other repos need not be.

## One-time setup

1. **Create the GitHub repo**: public, empty — *no* auto-created README or
   license (an initialized repo makes the first mirror push non-fast-forward).
   Name: `HomeAssistant` under the `SPOTBOT-ZA` org.
2. **Create a GitHub fine-grained PAT** limited to that repo with
   *Contents: Read and write* permission.
3. **Configure the push mirror in Gitea**: repo → Settings → Repository →
   Mirror Settings → *Push mirror*:
   - Git remote: `https://github.com/<org>/SPOTBOT_HOMEASSISTANT.git`
   - Username: the GitHub account name; Password: the PAT
   - Enable **"Sync when commits are pushed"** (plus the default 8 h interval)
4. Push `main` on Gitea and confirm the mirror shows up on GitHub, then set
   the repo description + topics (`home-assistant`, `hacs`, `integration`,
   `spotbot`) and enable Issues (HACS requires an issue tracker).

## What mirrors and what doesn't

- ✔ Branches and **tags** mirror.
- ✘ GitHub **Releases do not** — they're not git data. HACS versions from
  Releases, so `.github/workflows/release.yml` (running on the mirror)
  creates a Release automatically whenever a `v*` tag arrives.
- ✘ Gitea issues/PRs don't mirror; public issue tracking lives on GitHub.

## Care and feeding

- **PAT expiry silently stalls the mirror.** Gitea shows the failure only in
  the repo's mirror settings page. After a PAT rotation, update it there.
  Periodically (or after every release) verify the latest tag is visible on
  GitHub.
- **The mirror is public — assume everything here is world-readable, for
  ever.** One secret is published deliberately: the OAuth `client_secret`,
  shipped in `const.py` and documented in
  [server-setup.md](server-setup.md) §2, so users never have to obtain
  credentials. That is a considered trade — the client is capped to
  `epm 0x0803` and a token still needs the user's phone number and one-time
  PIN — and it means **rotating it is a breaking change for every
  installation**.
- Nothing else may follow it. In particular the client's
  **`jwt_signing_key` must never be committed**: it signs tokens, so leaking
  it is a different order of problem from leaking the client secret. It has
  never been in this repo — keep it that way.
- Force-pushes to `main` on Gitea will force-push the mirror; avoid.
