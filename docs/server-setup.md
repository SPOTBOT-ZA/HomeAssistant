# Server-side setup (one-time, per deployment)

The integration needs an OAuth client registered in the deployment it points
at — **SPOTBOT_APP_NEO** (see `const.DEFAULT_APP_FOLDER`). JWTs are signed
with a per-client key held in that deployment's database, so the client must
exist in the *same* deployment the authorize/token URLs belong to.

> Status: done. `sb_client_home_assistant` is registered on NEO and the
> integration has been driven end to end against it. The recipe below is what
> that client was built from, and what to repeat for another deployment.
>
> The live client differs from this recipe in two cosmetic ways —
> `client_name` is `HOME ASSISTANT` and `device_id_prefix` is `hass` (so
> sessions appear as `hass-…`, not `ha-…`). Neither affects behaviour; the
> fields that do are `is_public`, `endpoint_mask` and
> `token_expiry_seconds`.

## 1. Register the client

In the management console
(`https://www.spotbot-evo.co.za/SPOTBOT_APP_NEO/API/management/`, admin
account required), create a client with:

| Field | Value | Why |
|---|---|---|
| Client name | `Home Assistant` | auto-derives `client_id = sb_client_home_assistant` |
| `is_public` | `0` (confidential) | the server has **no PKCE**; a public client would let anyone with an intercepted code mint tokens |
| Redirect URIs | `["https://my.home-assistant.io/redirect/oauth"]` | the one fixed URL Home Assistant's OAuth helper uses for *every* user (the My Home Assistant relay redirects to the user's own instance in their browser). Exact match — no wildcard needed. |
| Endpoint mask | bits `[0, 1, 11]` → `0x0803` | status + control + account; matches the `google_home` preset. The console takes bit indexes, not the hex mask. |
| `token_expiry_seconds` | `3600` | up from the 600 s default; HA refreshes tokens pre-expiry, and hourly beats every-10-minutes |
| `device_id_prefix` | `ha` | HA sessions appear as `ha-…` devices in the user's signed-in device list |

**Record the response immediately** — `client_secret` and `jwt_signing_key`
are shown exactly once.

### Redirect URI notes

- Users who have disabled the `my` integration in HA redirect to
  `<their-HA-URL>/auth/external/callback` instead, which is different per
  household. v1 ships only the `my` URL (documented limitation). If needed
  later, options are: add `http://homeassistant.local:8123/auth/external/callback`
  for default installs, or the wildcard `*/auth/external/callback` (risk is
  bounded: codes are single-use, 10-minute, and exchanging one still requires
  the client secret).
- **Never** add a redirect URI containing `spotbot-evo.co.za` to this client —
  it would trigger the PWA token-bridge page instead of the `?code=` redirect.

## 2. Distribute the credentials

The registered client for `SPOTBOT_APP_NEO` is:

| Field | Value |
|---|---|
| Client ID | `sb_client_home_assistant` |
| Client secret | `c23a75477684575eb38c943b5cfbc3d849a68a0fcfe1c4d176076c37abcf09f2` |

These ship in the integration (`const.OAUTH_CLIENT_ID` /
`const.OAUTH_CLIENT_SECRET`) and are registered automatically through
`application_credentials.async_ensure_client_credential`, so users never see
the Application Credentials dialog. Changing the client here means changing
those constants and cutting a release.

The secret is deliberately low-value: possessing it grants nothing by itself —
every token issuance still requires the *user's* phone + OTP, and the client
is capped at epm `0x0803`. Still, the distribution options differ:

1. On request via support — keeps the secret out of the public GitHub mirror
   and search indexes; minor friction for users.
2. **Publish in the docs — chosen for v1.** Zero friction; the credentials
   live in [installation.md](installation.md) and therefore on the public
   mirror. This effectively makes the client public without PKCE. Precedent
   exists among HA integrations; it is the weakest option on paper, and is
   acceptable here only because of the epm cap and the phone+OTP requirement
   above.
3. Per-customer clients — not supported by the current one-secret-per-client
   schema.
4. **Long-term fix:** implement PKCE server-side, flip the client to
   `is_public = 1`, and drop the secret entirely (tracked in
   [roadmap](roadmap.md)).

Because the secret is public, rotating it is a breaking change for every
installed user — they must re-enter the new credentials by hand before the
integration works again. Treat a rotation as a release with release notes,
not a hotfix.

## 3. Later server work (not required for v1)

- Message/image history: expose the legacy `get_messages_for_spotbots`
  function as a REST route (messaging group, bit 7) so HA can show "last
  detection" without webhooks.
- Webhook serial mapping: webhook payloads carry a 13-digit serial; the REST
  API uses the `S…_…` form — document or normalize before the webhook-based
  `cloud_push` upgrade.
- PKCE support at `/authorize`/`/token` (see above).
- When cameras/outputs/webhook ship in the integration, widen the client's
  mask (bits 2, 5, 6 → `0x0867` with all three) — takes effect on the next
  token refresh.
