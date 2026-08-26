# Gitea → GitHub mirroring

HACS only installs from **public GitHub repositories**, and GitHub Actions
(hassfest/HACS validation, release creation) only run on GitHub. The Gitea
repo stays the source of truth; a push-mirror keeps a public GitHub clone in
sync.

## One-time setup

1. **Create the GitHub repo**: public, empty — *no* auto-created README or
   license (an initialized repo makes the first mirror push non-fast-forward).
   Name: `SPOTBOT_HOMEASSISTANT` under the chosen org
   (`GITHUB-ORG-TODO` — update `manifest.json` and all docs links once
   decided).
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
- **Never commit secrets** — the mirror is public. The OAuth `client_secret`
  lives only in the management console and the support-distribution channel,
  never in this repo (see [server-setup.md](server-setup.md)).
- Force-pushes to `main` on Gitea will force-push the mirror; avoid.
