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
KEY_SPEAKER_MUTE = "speaker_mute"
KEY_PANIC = "panic"
KEY_ONLINE = "online"
KEY_CAMERA_CONNECTIVITY = "camera_connectivity"

MANUFACTURER = "SpotBot"
MODEL = "SpotBot Evo"
