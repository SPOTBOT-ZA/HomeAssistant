/**
 * SpotBot card — a Lovelace card shaped like the card in the SpotBot PWA.
 *
 * One card per SpotBot: a header that reflects whether the device is
 * reachable, a row of numbered camera indicators coloured by detection, a
 * second row for armed response, the snoozed cameras with the time their
 * snooze runs out, and the snooze controls.
 *
 * It reads only the integration's own entities, matched by their unique_id
 * shape (<serial>_<key>[_cam<n>]) via the entity registry the frontend
 * already holds, so nothing here needs to be configured by hand beyond the
 * device.
 *
 * Deliberately not reproduced from the PWA card:
 *  - the last-detection message preview and image. The REST API exposes no
 *    messages endpoint, so Home Assistant never sees them (roadmap §4).
 *  - the premium badge, access level, and the pin icon, which are PWA-local
 *    or not exposed as entities.
 */

const CONN_FINE = 0;
const CONN_WARNING = 1;
const CONN_ERROR = 2;

class SpotBotCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("hui-entities-card-editor");
  }

  static getStubConfig(hass) {
    const first = Object.keys(hass.states).find((e) =>
      e.startsWith("binary_sensor.") && e.endsWith("_connectivity"),
    );
    return { device: first ? first.split(".")[1].replace(/_connectivity$/, "") : "" };
  }

  setConfig(config) {
    if (!config.device) {
      throw new Error(
        'Set "device": the SpotBot device name, e.g. device: spotbot_bosplaas',
      );
    }
    this._config = config;
    this._built = false;
  }

  getCardSize() {
    return 3;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  /** Entities belonging to this device, by the slug the integration uses. */
  _entities() {
    const slug = this._config.device;
    const out = { cameras: new Map() };
    for (const id of Object.keys(this._hass.states)) {
      const [domain, object] = id.split(".", 2);
      if (!object.startsWith(slug)) continue;
      const rest = object.slice(slug.length).replace(/^_/, "");

      if (domain === "binary_sensor" && rest === "connectivity") out.online = id;
      else if (domain === "switch" && rest === "speaker_mute") out.mute = id;
      else if (domain === "button" && rest === "snooze") out.snooze = id;
      else if (domain === "button" && rest === "unsnooze") out.unsnooze = id;
      else {
        // Per-camera: "<camera name>_detection" and friends. The camera name
        // is whatever the device calls it, so it is taken as the remainder.
        const m = rest.match(/^(.*)_(detection|armed_response|connectivity|snoozed)$/);
        if (!m) continue;
        const [, cam, kind] = m;
        if (!cam) continue;
        if (!out.cameras.has(cam)) out.cameras.set(cam, {});
        out.cameras.get(cam)[kind] = id;
      }
    }
    return out;
  }

  _state(id) {
    return id ? this._hass.states[id] : undefined;
  }

  _press(entityId) {
    const [domain] = entityId.split(".", 1);
    const service = domain === "button" ? "press" : "toggle";
    this._hass.callService(domain, service, { entity_id: entityId });
  }

  _camIndicator(cam, entities) {
    const conn = this._state(entities.connectivity);
    const code = conn?.attributes?.conn_status;
    // conn_status is a fault code, not a flag: 0 is "Fine". Anything else is
    // drawn instead of the normal indicator, exactly as the apps do.
    if (code === CONN_WARNING) return { icon: "mdi:alert", cls: "warn", title: "Connection warning" };
    if (code === CONN_ERROR) return { icon: "mdi:video-off", cls: "error", title: "No video" };
    if (code !== undefined && code !== CONN_FINE && code !== null) {
      return { icon: "mdi:help-circle-outline", cls: "unknown", title: `Unknown status (${code})` };
    }
    return null;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const e = this._entities();
    const online = this._state(e.online);
    const isOnline = online?.state === "on";

    if (!this._built) {
      this.innerHTML = `
        <ha-card>
          <div class="sb-header"><span class="sb-title"></span><span class="sb-status"></span></div>
          <div class="sb-body">
            <div class="sb-row sb-detection"><span class="sb-label">Detection</span><div class="sb-grid"></div></div>
            <div class="sb-row sb-ar"><span class="sb-label">Armed response</span><div class="sb-grid"></div></div>
            <div class="sb-snoozed"></div>
            <div class="sb-actions"></div>
          </div>
        </ha-card>
        <style>
          .sb-header{display:flex;align-items:center;justify-content:space-between;
            padding:12px 16px;border-bottom:1px solid var(--divider-color);}
          .sb-title{font-weight:600;}
          .sb-status{font-size:.85em;padding:2px 8px;border-radius:10px;
            background:var(--label-badge-green,#3cb55c);color:#fff;}
          .sb-status.off{background:var(--label-badge-red,#df4c1e);}
          .sb-body{padding:12px 16px;}
          .sb-row{display:flex;align-items:center;gap:12px;margin-bottom:10px;}
          .sb-label{font-size:.85em;color:var(--secondary-text-color);min-width:110px;}
          .sb-grid{display:flex;flex-wrap:wrap;gap:6px;}
          .sb-cam{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;
            justify-content:center;font-size:.8em;cursor:pointer;border:none;
            background:var(--disabled-text-color);color:#fff;}
          .sb-cam.on{background:var(--label-badge-green,#3cb55c);}
          .sb-cam.ar-on{background:#0bb6d1;}
          .sb-cam.warn{background:#fad105;color:#333;}
          .sb-cam.error{background:#df4c1e;}
          .sb-cam.unknown{background:#099bb3;}
          .sb-snoozed{font-size:.85em;color:var(--secondary-text-color);margin:8px 0;}
          .sb-actions{display:flex;gap:8px;flex-wrap:wrap;}
          .sb-actions mwc-button{--mdc-theme-primary:var(--primary-color);}
          .sb-empty{color:var(--secondary-text-color);font-size:.9em;}
        </style>`;
      this._built = true;
    }

    const q = (s) => this.querySelector(s);
    q(".sb-title").textContent =
      online?.attributes?.friendly_name?.replace(/ Connectivity$/i, "") || this._config.device;
    const status = q(".sb-status");
    status.textContent = isOnline ? "Online" : "Offline";
    status.classList.toggle("off", !isOnline);

    const cams = [...e.cameras.entries()].sort((a, b) => a[0].localeCompare(b[0]));

    const fill = (grid, kind, onClass) => {
      grid.innerHTML = "";
      let any = false;
      cams.forEach(([cam, ents], i) => {
        const id = ents[kind];
        if (!id) return; // e.g. no armed response on an "NA" camera
        any = true;
        const st = this._state(id);
        const btn = document.createElement("button");
        btn.className = "sb-cam";
        const fault = this._camIndicator(cam, ents);
        if (fault) {
          btn.classList.add(fault.cls);
          btn.innerHTML = `<ha-icon icon="${fault.icon}" style="--mdc-icon-size:18px"></ha-icon>`;
          btn.title = `${cam}: ${fault.title}`;
        } else {
          if (st?.state === "on") btn.classList.add(onClass);
          btn.textContent = String(i + 1);
          btn.title = `${cam.replace(/_/g, " ")}: ${st?.state === "on" ? "on" : "off"}`;
        }
        btn.addEventListener("click", () => this._press(id));
        grid.appendChild(btn);
      });
      return any;
    };

    fill(q(".sb-detection .sb-grid"), "detection", "on");
    const hasAr = fill(q(".sb-ar .sb-grid"), "armed_response", "ar-on");
    q(".sb-ar").style.display = hasAr ? "" : "none";

    const snoozed = cams
      .map(([cam, ents]) => [cam, this._state(ents.snoozed)])
      .filter(([, st]) => st?.state === "on");
    q(".sb-snoozed").textContent = snoozed.length
      ? "Snoozed: " +
        snoozed
          .map(([cam, st]) => {
            const until = st.attributes?.snoozed_until;
            return cam.replace(/_/g, " ") + (until ? ` until ${until}` : "");
          })
          .join(", ")
      : "";

    const actions = q(".sb-actions");
    actions.innerHTML = "";
    const add = (label, id) => {
      if (!id) return;
      const b = document.createElement("mwc-button");
      b.textContent = label;
      b.addEventListener("click", () => this._press(id));
      actions.appendChild(b);
    };
    add("Snooze", e.snooze);
    add("Unsnooze", e.unsnooze);
    if (e.mute) {
      add(this._state(e.mute)?.state === "on" ? "Unmute speaker" : "Mute speaker", e.mute);
    }

    if (!cams.length) {
      q(".sb-detection").style.display = "none";
      q(".sb-snoozed").innerHTML = '<span class="sb-empty">No cameras reported.</span>';
    } else {
      q(".sb-detection").style.display = "";
    }
  }
}

customElements.define("spotbot-card", SpotBotCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "spotbot-card",
  name: "SpotBot",
  description: "Detection, armed response and snooze for one SpotBot, laid out like the SpotBot app.",
});

console.info("%c SPOTBOT-CARD %c loaded ", "background:#0bb6d1;color:#fff", "");
