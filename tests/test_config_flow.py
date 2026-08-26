"""Tests for the SpotBot OAuth2 config flow."""

from __future__ import annotations

import json
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_entry_oauth2_flow

from pytest_homeassistant_custom_component.common import load_fixture
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.spotbot.const import (
    DEFAULT_BASE_URL,
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
)

REDIRECT_URI = "https://example.com/auth/external/callback"


async def test_full_flow(
    hass: HomeAssistant,
    hass_client_no_auth,
    aioclient_mock: AiohttpClientMocker,
    current_request_with_host: None,
    setup_credentials: None,
) -> None:
    """The full happy path: authorize -> callback -> token -> userinfo -> entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {"flow_id": result["flow_id"], "redirect_uri": REDIRECT_URI},
    )

    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"].startswith(OAUTH2_AUTHORIZE)
    assert f"state={state}" in result["url"]

    client = await hass_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "access_token": "mock-access",
            "refresh_token": "mock-refresh",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
    )
    aioclient_mock.get(
        f"{DEFAULT_BASE_URL}/oauth/userinfo",
        json=json.loads(load_fixture("userinfo.json")),
    )

    with patch(
        "custom_components.spotbot.async_setup_entry", return_value=True
    ) as mock_setup:
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test User"
    entry = result["result"]
    assert entry.unique_id == "42"
    assert entry.data["token"]["refresh_token"] == "mock-refresh"
    assert len(mock_setup.mock_calls) == 1


async def test_duplicate_account_aborts(
    hass: HomeAssistant,
    hass_client_no_auth,
    aioclient_mock: AiohttpClientMocker,
    current_request_with_host: None,
    setup_credentials: None,
    config_entry,
) -> None:
    """A second flow for the same sb_id aborts as already_configured."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {"flow_id": result["flow_id"], "redirect_uri": REDIRECT_URI},
    )
    client = await hass_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "access_token": "mock-access",
            "refresh_token": "mock-refresh",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
    )
    aioclient_mock.get(
        f"{DEFAULT_BASE_URL}/oauth/userinfo",
        json=json.loads(load_fixture("userinfo.json")),
    )

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_userinfo_failure_aborts(
    hass: HomeAssistant,
    hass_client_no_auth,
    aioclient_mock: AiohttpClientMocker,
    current_request_with_host: None,
    setup_credentials: None,
) -> None:
    """If userinfo cannot be fetched, the flow aborts with cannot_connect."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {"flow_id": result["flow_id"], "redirect_uri": REDIRECT_URI},
    )
    client = await hass_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "access_token": "mock-access",
            "refresh_token": "mock-refresh",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
    )
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/oauth/userinfo", status=500)

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
