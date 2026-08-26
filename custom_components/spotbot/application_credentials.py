"""Application credentials platform for the SpotBot integration.

The SpotBot OAuth server publishes no discovery document (/.well-known) and
no JWKS, so the authorize/token URLs are fixed constants. They contain the
deployment folder (see const.DEFAULT_APP_FOLDER) — the OAuth client
``sb_client_home_assistant`` must be registered in that same deployment's
management console, because JWTs are signed with a per-client key held in
that deployment's database.
"""

from __future__ import annotations

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import DEFAULT_BASE_URL, OAUTH2_AUTHORIZE, OAUTH2_TOKEN


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return the SpotBot authorization server."""
    return AuthorizationServer(authorize_url=OAUTH2_AUTHORIZE, token_url=OAUTH2_TOKEN)


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Placeholders for the application credentials dialog text."""
    return {
        "oauth_url": DEFAULT_BASE_URL,
        "docs_url": "https://github.com/GITHUB-ORG-TODO/SPOTBOT_HOMEASSISTANT/blob/main/docs/installation.md",
    }
