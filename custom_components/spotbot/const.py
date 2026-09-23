"""Constants for the SpotBot integration."""

from datetime import timedelta

DOMAIN = "spotbot"

# --- Deployment / base URL -------------------------------------------------
# SpotBot deployments live at https://www.spotbot-evo.co.za/<APP_FOLDER>/API.
# Home Assistant is served by the SPOTBOT_APP_NEO deployment; other
# deployments are SPOTBOT_APP (production PWA), SPOTBOT_APP_PAUL,
# SPOTBOT_APP_NEO_FAF and SPOTBOT_APP_FRANCOIS.
#
# The OAuth authorize/token URLs are derived from this base and handed to
# Home Assistant's application_credentials platform, which only supports one
# fixed AuthorizationServer per domain — so this constant is the single edit
# point when targeting a different deployment (the OAuth client must then
# also be registered in THAT deployment's management console).
# Every config entry stores its base_url in entry data (CONF_BASE_URL), so
# entries are self-describing and a future deployment picker needs no
# migration.
DEFAULT_HOST = "https://www.spotbot-evo.co.za"
DEFAULT_APP_FOLDER = "SPOTBOT_APP_NEO"
DEFAULT_BASE_URL = f"{DEFAULT_HOST}/{DEFAULT_APP_FOLDER}/API"

OAUTH2_AUTHORIZE = f"{DEFAULT_BASE_URL}/oauth/authorize"
OAUTH2_TOKEN = f"{DEFAULT_BASE_URL}/oauth/token"

CONF_BASE_URL = "base_url"
# Which oauth device id the SpotBots were last told to sync for, and which of
# them accepted it. Signing in mints a new device id that the firmware does
# not know until it syncs, so the sync is redone whenever this no longer
# matches the entry's token, and retried for any serial that was offline.
CONF_SYNCED_DEVICE_ID = "synced_device_id"
CONF_SYNCED_SERIALS = "synced_serials"

# --- Built-in OAuth client -------------------------------------------------
# One client serves every installation, so the integration registers it
# itself (see async_setup) and the Application Credentials dialog never
# appears. Shipping the secret is the deliberate choice recorded in
# docs/server-setup.md §2: it identifies the integration, not the user.
# Issuing a token still requires the user's own phone number and one-time
# PIN, and the client is capped to the status, control and account endpoints
# (epm 0x0803). Rotating it is therefore a breaking change for every
# installation — see the note in that doc before changing these.
OAUTH_CLIENT_ID = "sb_client_home_assistant"
OAUTH_CLIENT_SECRET = "c23a75477684575eb38c943b5cfbc3d849a68a0fcfe1c4d176076c37abcf09f2"
OAUTH_CLIENT_NAME = "SpotBot"

# --- Polling ---------------------------------------------------------------
# Every REST call is a synchronous MQTT round-trip on the server that parks a
# PHP worker for up to ~8 s, so poll gently and never stampede.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=120)
# Max simultaneous per-device requests during a coordinator refresh.
PARALLEL_DEVICE_REQUESTS = 2
# aiohttp total timeout; the gateway itself gives up at 8-15 s per route.
API_TIMEOUT = 30

# --- Entity keys -----------------------------------------------------------
KEY_DETECTION = "detection"
KEY_ARMED_RESPONSE = "armed_response"
KEY_SNOOZE = "snooze"
KEY_UNSNOOZE = "unsnooze"
KEY_SPEAKER_MUTE = "speaker_mute"
KEY_PANIC = "panic"
KEY_ONLINE = "online"
KEY_CAMERA_CONNECTIVITY = "camera_connectivity"
KEY_CAMERA_SNOOZED = "camera_snoozed"

# --- cam_status.conn_status ------------------------------------------------
# A fault code, not a flag. 0 is the healthy value — the apps hide the
# indicator entirely for it and only draw something for the rest.
CONN_STATUS_OK = 0
CONN_STATUS_WARNING = 1
CONN_STATUS_ERROR = 2

MANUFACTURER = "SpotBot"
MODEL = "SpotBot Evo"
