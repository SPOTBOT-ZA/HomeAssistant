"""Async client for the SpotBot REST API.

The API is an HTTP->MQTT RPC gateway: every device call is relayed to the
device over MQTT and blocks server-side until the device answers or the
route's timeout expires. Notable server behaviors this client absorbs:

- 504 gateway_timeout is the NORMAL "device is offline" signal.
- An expired access token yields 403 (not 401) from /api/v2/*; an epm
  (endpoint-mask) denial is ALSO 403. The two are disambiguated by probing
  /oauth/userinfo, which only fails for a bad token.
- ``cam_status`` inside a status payload may arrive as a JSON-encoded string
  instead of a list.
- /devices/{serial}/presence returns a FLATTENED object (serial, online, ts,
  fw) and 404 problem+json ``no_presence`` when no retained message exists.
- Errors are RFC 7807 application/problem+json.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import aiohttp

from homeassistant.helpers import config_entry_oauth2_flow

from .const import API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class SpotBotApiError(Exception):
    """Base error for SpotBot API failures."""


class SpotBotConnectionError(SpotBotApiError):
    """Network-level failure talking to the API."""


class SpotBotAuthError(SpotBotApiError):
    """The access token is invalid and could not be refreshed."""


class SpotBotPermissionError(SpotBotApiError):
    """The OAuth client's endpoint mask (epm) does not allow this endpoint."""


class SpotBotDeviceOfflineError(SpotBotApiError):
    """The device did not answer over MQTT (HTTP 504)."""


def _as_bool(value: Any) -> bool:
    """Coerce the API's loosely-typed flags ("1", 1, "true", True) to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "on", "yes", "act", "active")
    return False


def _is_applicable(value: Any) -> bool:
    """False when a flag says the feature does not apply to this camera.

    The API spells that "NA" (seen on ar_onoff). A missing or empty value is
    treated the same way: there is nothing to control and nothing to show.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().upper() not in ("", "NA", "N/A", "NONE", "NULL")
    return True


@dataclass
class SpotBotDevice:
    """One row of GET /api/v2/account/devices."""

    serial: str
    name: str
    bot_title: str
    access_level: str
    premium_level: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> SpotBotDevice:
        return cls(
            serial=str(data.get("Serial", "")),
            name=str(data.get("Name") or ""),
            bot_title=str(data.get("Bot_title") or ""),
            access_level=str(data.get("Access_level") or ""),
            premium_level=str(data.get("premium_level") or ""),
            raw=data,
        )

    @property
    def display_name(self) -> str:
        return self.bot_title or self.name or self.serial


@dataclass
class SpotBotCamera:
    """One entry of a status payload's cam_status[]."""

    cam_nr: str
    name: str
    detection_on: bool
    armed_response_on: bool
    # False when the camera reports ar_onoff as "NA": armed response is not
    # provisioned for it, and no armed-response entity should exist. The
    # device accepts /ar_on and /ar_off for such a camera and returns 200
    # while changing nothing, so there is no way to tell from the command
    # whether it took — only this field says so up front.
    armed_response_supported: bool
    connected: bool
    snoozed: bool
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> SpotBotCamera:
        ar = data.get("ar_onoff")
        return cls(
            cam_nr=str(data.get("camnr", "")),
            name=str(data.get("camname") or ""),
            # Verified live: onoff is 0/1 as a number; ar_onoff is 0/1 as a
            # number or the string "NA".
            detection_on=_as_bool(data.get("onoff")),
            armed_response_on=_as_bool(ar),
            armed_response_supported=_is_applicable(ar),
            connected=_as_bool(data.get("conn_status")),
            snoozed=_as_bool(data.get("snooze")),
            raw=data,
        )


@dataclass
class SpotBotStatus:
    """GET /api/v2/devices/{serial}/status -> data."""

    sw_version: str
    speaker_muted: bool
    snoozed: bool
    cameras: list[SpotBotCamera]
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> SpotBotStatus:
        cam_status = data.get("cam_status") or []
        # The device sometimes sends cam_status as a JSON-encoded string.
        if isinstance(cam_status, str):
            try:
                cam_status = json.loads(cam_status)
            except ValueError:
                _LOGGER.warning("Unparseable cam_status string: %s", cam_status)
                cam_status = []
        if not isinstance(cam_status, list):
            cam_status = []
        return cls(
            sw_version=str(data.get("sw_version") or ""),
            # Verified live: Mute_status is the string "true"/"false", not a
            # number — _as_bool already reads both.
            speaker_muted=_as_bool(data.get("Mute_status")),
            snoozed=_as_bool(data.get("snooze")),
            cameras=[SpotBotCamera.from_json(c) for c in cam_status if isinstance(c, dict)],
            raw=data,
        )


@dataclass
class SpotBotPresence:
    """GET /api/v2/devices/{serial}/presence (flattened code shape)."""

    online: bool
    ts: int | None
    fw: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> SpotBotPresence:
        ts = data.get("ts")
        return cls(
            online=_as_bool(data.get("online")),
            ts=int(ts) if isinstance(ts, (int, float)) else None,
            fw=str(data.get("fw") or ""),
            raw=data,
        )


class AsyncConfigEntryAuth:
    """Provide a valid access token from the config entry's OAuth2 session."""

    def __init__(self, oauth_session: config_entry_oauth2_flow.OAuth2Session) -> None:
        self._oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        try:
            await self._oauth_session.async_ensure_token_valid()
        except aiohttp.ClientResponseError as err:
            if err.status in (400, 401, 403):
                raise SpotBotAuthError(f"Token refresh rejected: {err.status}") from err
            raise SpotBotConnectionError(f"Token refresh failed: {err}") from err
        except aiohttp.ClientError as err:
            raise SpotBotConnectionError(f"Token refresh failed: {err}") from err
        return self._oauth_session.token["access_token"]


class SpotBotApiClient:
    """Minimal typed wrapper over the SpotBot v2 REST API."""

    def __init__(
        self,
        auth: AsyncConfigEntryAuth,
        websession: aiohttp.ClientSession,
        base_url: str,
    ) -> None:
        """base_url is e.g. https://www.spotbot-evo.co.za/SPOTBOT_APP_NEO/API."""
        self._auth = auth
        self._websession = websession
        self._base_url = base_url.rstrip("/")

    @property
    def base_url(self) -> str:
        return self._base_url

    async def _request(
        self, method: str, path: str, *, oauth_path: bool = False, **kwargs: Any
    ) -> Any:
        """Perform an authenticated request and normalize error handling."""
        token = await self._auth.async_get_access_token()
        prefix = "/oauth" if oauth_path else "/api/v2"
        url = f"{self._base_url}{prefix}{path}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with self._websession.request(
                method,
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                **kwargs,
            ) as resp:
                if resp.status == 504:
                    raise SpotBotDeviceOfflineError(path)
                if resp.status == 401:
                    raise SpotBotAuthError("401 unauthorized")
                if resp.status == 403:
                    raise await self._classify_403(token, path)
                if resp.status == 404:
                    body = await self._problem_json(resp)
                    if "no_presence" in str(body.get("type", "")):
                        return None
                    raise SpotBotApiError(f"404 on {path}: {body.get('detail')}")
                if resp.status >= 400:
                    body = await self._problem_json(resp)
                    raise SpotBotApiError(
                        f"{resp.status} on {path}: {body.get('title')} {body.get('detail')}"
                    )
                return await resp.json(content_type=None)
        except asyncio.TimeoutError as err:
            raise SpotBotConnectionError(f"Timeout on {path}") from err
        except aiohttp.ClientError as err:
            raise SpotBotConnectionError(f"Connection error on {path}: {err}") from err

    @staticmethod
    async def _problem_json(resp: aiohttp.ClientResponse) -> dict[str, Any]:
        try:
            body = await resp.json(content_type=None)
            return body if isinstance(body, dict) else {}
        except (ValueError, aiohttp.ClientError):
            return {}

    async def _classify_403(self, token: str, path: str) -> SpotBotApiError:
        """Disambiguate 403: expired/invalid token vs endpoint-mask denial.

        The gateway returns 403 both for a bad/expired JWT and for an epm
        (endpoint mask) denial. /oauth/userinfo succeeds for any valid token,
        so it separates the two without side effects.
        """
        try:
            async with self._websession.get(
                f"{self._base_url}/oauth/userinfo",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as probe:
                if probe.status == 200:
                    return SpotBotPermissionError(
                        f"Endpoint mask denies {path}; adjust the OAuth client's "
                        "epm in the SpotBot management console"
                    )
        except aiohttp.ClientError:
            pass
        return SpotBotAuthError("403 with invalid token")

    # --- OAuth-side helpers ------------------------------------------------

    async def async_get_userinfo(self) -> dict[str, Any]:
        """Return the token's identity; also the config-flow connectivity probe."""
        return await self._request("GET", "/userinfo", oauth_path=True)

    # --- Account -----------------------------------------------------------

    async def async_get_devices(self) -> list[SpotBotDevice]:
        body = await self._request("GET", "/account/devices")
        rows = body.get("data") if isinstance(body, dict) else None
        if not isinstance(rows, list):
            return []
        return [SpotBotDevice.from_json(r) for r in rows if isinstance(r, dict)]

    # --- Per-device state --------------------------------------------------

    async def async_get_status(self, serial: str) -> SpotBotStatus:
        body = await self._request("GET", f"/devices/{serial}/status")
        return SpotBotStatus.from_json(body.get("data") or {})

    async def async_get_presence(self, serial: str) -> SpotBotPresence | None:
        body = await self._request("GET", f"/devices/{serial}/presence")
        if body is None:  # 404 no_presence
            return None
        return SpotBotPresence.from_json(body)

    # --- Commands ----------------------------------------------------------

    async def async_set_detection(
        self, serial: str, cam: str | Literal["all"], on: bool
    ) -> None:
        action = "on" if on else "off"
        await self._request("POST", f"/devices/{serial}/{action}/{cam}")

    async def async_set_armed_response(
        self, serial: str, cam: str | Literal["all"], on: bool
    ) -> None:
        action = "ar_on" if on else "ar_off"
        await self._request("POST", f"/devices/{serial}/{action}/{cam}")

    async def async_snooze(self, serial: str, cam: str | Literal["all"] = "all") -> None:
        await self._request("POST", f"/devices/{serial}/snooze/{cam}")

    async def async_unsnooze(self, serial: str, cam: str | Literal["all"] = "all") -> None:
        await self._request("POST", f"/devices/{serial}/unsnooze/{cam}")

    async def async_set_speaker_mute(self, serial: str, muted: bool) -> None:
        """Mute or unmute the device speaker.

        The body key is "todo", "1" to mute and "0" to unmute. Anything else
        is ignored by the device, which then falls through to unmuting — so
        the old {"mute": "on"|"off"} body silently unmuted in both
        directions and mute could never be engaged.

        Only swagger-internal.php documents this route; the public spec
        omits it entirely.
        """
        await self._request(
            "POST",
            f"/devices/{serial}/speaker_mute",
            json={"todo": "1" if muted else "0"},
        )

    async def async_panic(self, serial: str) -> None:
        await self._request("POST", f"/devices/{serial}/panic")
