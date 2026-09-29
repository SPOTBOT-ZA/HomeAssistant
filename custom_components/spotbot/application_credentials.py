"""Application credentials platform for the SpotBot integration.

The SpotBot OAuth server publishes no discovery document (/.well-known) and
no JWKS, so the authorize/token URLs are fixed constants. They contain the
deployment folder (see const.DEFAULT_APP_FOLDER) — the OAuth client
``sb_client_home_assistant`` must be registered in that same deployment's
management console, because JWTs are signed with a per-client key held in
that deployment's database.
"""

from __future__ import annotations

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .const import (
    DEFAULT_BASE_URL,
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_NAME,
    OAUTH_CLIENT_SECRET,
)


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return the SpotBot authorization server."""
    return AuthorizationServer(authorize_url=OAUTH2_AUTHORIZE, token_url=OAUTH2_TOKEN)


async def async_ensure_client_credential(hass: HomeAssistant) -> None:
    """Register the built-in SpotBot OAuth client if it is not there yet.

    Called from the config flow rather than only from async_setup: on a
    fresh install Home Assistant does not set the integration up until a
    config entry exists, so async_setup has never run by the time the user
    clicks Add Integration — the credential has to be in place before the
    flow looks for an implementation, or it aborts with missing_credentials.

    Idempotent: application_credentials keys items by "<domain>.<client_id>"
    and skips one that already exists.
    """
    await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass,
        DOMAIN,
        ClientCredential(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_CLIENT_NAME),
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Placeholders for the application credentials dialog text."""
    return {
        "oauth_url": DEFAULT_BASE_URL,
        "docs_url": "https://github.com/SPOTBOT-ZA/HomeAssistant/blob/main/docs/installation.md",
    }
