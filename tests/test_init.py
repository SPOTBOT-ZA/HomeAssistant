"""Tests for SpotBot integration setup, offline handling and unload."""

from __future__ import annotations

import json

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import load_fixture
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.spotbot.api import SpotBotStatus
from custom_components.spotbot.const import (
    CONF_SYNCED_DEVICE_ID,
    CONF_SYNCED_SERIALS,
    DEFAULT_BASE_URL,
)

SERIAL = "S011224_8980947"


def _mock_api(
    aioclient_mock: AiohttpClientMocker,
    presence_status: int = 200,
    status_payload: dict | None = None,
) -> None:
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
        json=status_payload or json.loads(load_fixture("status.json")),
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

    # 1 device with 1 camera: speaker mute + detection + armed response.
    # Snooze is a button, not a switch — the device expires it by itself.
    assert len(hass.states.async_entity_ids("switch")) == 3
    # device online + camera connectivity
    assert len(hass.states.async_entity_ids("binary_sensor")) == 2
    # snooze + unsnooze; panic is disabled by default, so it has no state
    assert len(hass.states.async_entity_ids("button")) == 2

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


async def test_na_camera_gets_no_armed_response_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_credentials: None,
    config_entry,
) -> None:
    """A camera reporting ar_onoff "NA" has no armed response, so no entity.

    The API accepts /ar_on and /ar_off for such a camera and answers 200
    while the device ignores it, so a switch here would read off and
    silently do nothing. Detection must still be there.
    """
    status = json.loads(load_fixture("status.json"))
    status["data"]["cam_status"][0]["ar_onoff"] = "NA"
    _mock_api(aioclient_mock, status_payload=status)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    switches = hass.states.async_entity_ids("switch")
    assert not [e for e in switches if e.endswith("_armed_response")]
    assert [e for e in switches if e.endswith("_detection")]
    # speaker mute + detection, with armed response gone
    assert len(switches) == 2


def test_na_armed_response_is_not_applicable() -> None:
    """"NA" is not a boolean — it means the feature is absent."""
    payload = json.loads(load_fixture("status.json"))["data"]
    payload["cam_status"][0]["ar_onoff"] = "NA"
    cam = SpotBotStatus.from_json(payload).cameras[0]
    assert cam.armed_response_supported is False
    assert cam.armed_response_on is False

    payload["cam_status"][0]["ar_onoff"] = 1
    cam = SpotBotStatus.from_json(payload).cameras[0]
    assert cam.armed_response_supported is True
    assert cam.armed_response_on is True


async def test_sign_in_syncs_the_device_id_to_the_spotbots(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_credentials: None,
    config_entry,
) -> None:
    """Each SpotBot is told to pick up this session's oauth device id.

    Signing in mints a device id the firmware does not know until it syncs,
    and until then the device refuses every command with an RPC-level
    "Authentication failed" while the entities all look healthy — so the
    absence of this call is invisible until someone flips a switch.

    It is recorded against the device id rather than run on every setup: a
    restart reuses the same id, and each sync is an MQTT round trip.
    """
    hass.config_entries.async_update_entry(
        config_entry,
        data={
            **config_entry.data,
            "token": {**config_entry.data["token"], "oauth_device_id": "hass-test"},
        },
    )
    _mock_api(aioclient_mock)
    aioclient_mock.post(
        f"{DEFAULT_BASE_URL}/api/v2/devices/{SERIAL}/users/sync",
        json={"serial": SERIAL, "data": {"success": True}},
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    syncs = [c for c in aioclient_mock.mock_calls if c[1].path.endswith("/users/sync")]
    assert len(syncs) == 1
    assert syncs[0][2] == {"device_id": "hass-test", "sbid_p": "42"}
    assert config_entry.data[CONF_SYNCED_DEVICE_ID] == "hass-test"
    assert config_entry.data[CONF_SYNCED_SERIALS] == [SERIAL]

    # Same device id on the next setup: nothing to re-sync.
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    syncs = [c for c in aioclient_mock.mock_calls if c[1].path.endswith("/users/sync")]
    assert len(syncs) == 1


def test_conn_status_is_a_fault_code_not_a_flag() -> None:
    """Only conn_status 0 means connected.

    0 is "Fine" — the apps hide the indicator for it and draw something only
    for 1 (warning), 2 (error) and anything unrecognised. Reading the field
    as a boolean inverts the sensor and reports every healthy camera as
    disconnected.
    """
    payload = json.loads(load_fixture("status.json"))["data"]

    for code, connected in ((0, True), (1, False), (2, False), (7, False)):
        payload["cam_status"][0]["conn_status"] = code
        cam = SpotBotStatus.from_json(payload).cameras[0]
        assert cam.connected is connected, f"conn_status {code}"
        assert cam.conn_status == code

    # Loose typing: the value may arrive as a string.
    payload["cam_status"][0]["conn_status"] = "0"
    assert SpotBotStatus.from_json(payload).cameras[0].connected is True

    # Missing or unparseable: not connected, and no crash.
    payload["cam_status"][0]["conn_status"] = "weird"
    cam = SpotBotStatus.from_json(payload).cameras[0]
    assert cam.connected is False
    assert cam.conn_status is None


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
    # That fixture carries conn_status 0, which is "Fine" — connected.
    assert cam.connected is True
