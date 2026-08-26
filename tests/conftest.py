"""Shared fixtures for the SpotBot integration tests."""

from __future__ import annotations

import time

import pytest

from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.spotbot.const import CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN

CLIENT_ID = "sb_client_home_assistant"
CLIENT_SECRET = "mock-client-secret"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components/ in the test instance."""
    return


@pytest.fixture
async def setup_credentials(hass: HomeAssistant) -> None:
    """Register mock SpotBot application credentials."""
    assert await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass, DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET)
    )


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """A config entry with a still-valid token."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="42",
        title="Test User",
        data={
            "auth_implementation": DOMAIN,
            "token": {
                "access_token": "mock-access",
                "refresh_token": "mock-refresh",
                "token_type": "Bearer",
                "expires_in": 3600,
                "expires_at": time.time() + 3600,
            },
            CONF_BASE_URL: DEFAULT_BASE_URL,
        },
    )
    entry.add_to_hass(hass)
    return entry
