"""Tests for SpotBot integration setup, offline handling and unload."""

from __future__ import annotations

import json

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import load_fixture
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.spotbot.api import SpotBotStatus
from custom_components.spotbot.const import DEFAULT_BASE_URL

SERIAL = "S011224_8980947"


def _mock_api(aioclient_mock: AiohttpClientMocker, presence_status: int = 200) -> None:
    aioclient_mock.get(
        f"{DEFAULT_BASE_URL}/api/v2/account/devices",
        json=json.loads(load_fixture("devices.json")),
    )
    if presence_status == 200:
        aioclient_mock.get(
            f"{DEFAULT_BASE_URL}/api/v2/devices/{SERIAL}/presence",
            json=json.loads(load_fixture("presence.json")),
        )
    else:
        aioclient_mock.get(
            f"{DEFAULT_BASE_URL}/api/v2/devices/{SERIAL}/presence",
            status=presence_status,
        )
    aioclient_mock.get(
        f"{DEFAULT_BASE_URL}/api/v2/devices/{SERIAL}/status",
        json=json.loads(load_fixture("status.json")),
    )


async def test_setup_and_unload(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_credentials: None,
    config_entry,
) -> None:
    """Entry sets up, creates entities, and unloads cleanly."""
    _mock_api(aioclient_mock)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    # 1 device with 1 camera: snooze + speaker mute + detection + armed response
    assert len(hass.states.async_entity_ids("switch")) == 4
    # device online + camera connectivity
    assert len(hass.states.async_entity_ids("binary_sensor")) == 2
    # panic button is disabled by default -> no state
    assert len(hass.states.async_entity_ids("button")) == 0

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_device_offline_is_not_a_setup_failure(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_credentials: None,
    config_entry,
) -> None:
    """A 504 (device offline) must not fail setup; entities go unavailable."""
    _mock_api(aioclient_mock, presence_status=504)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    for entity_id in hass.states.async_entity_ids("switch"):
        assert hass.states.get(entity_id).state == "unavailable"


def test_status_parses_cam_status_string() -> None:
    """cam_status arriving as a JSON-encoded string is coerced to a list."""
    payload = json.loads(load_fixture("status_cam_string.json"))["data"]
    status = SpotBotStatus.from_json(payload)
    assert status.speaker_muted is True
    assert status.snoozed is True
    assert len(status.cameras) == 1
    cam = status.cameras[0]
    assert cam.cam_nr == "1"
    assert cam.detection_on is False
    assert cam.armed_response_on is True
    assert cam.connected is False
