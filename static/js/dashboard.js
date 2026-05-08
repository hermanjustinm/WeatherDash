/* WeatherDash — dashboard.js */
"use strict";

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  alerts: [],
  currentAlertIndex: 0,
  cameras: [],
  radarLayer: "rain",
  map: null,
  rainviewerLayer: null,
  rainviewerFrames: [],
  rainviewerCurrentFrame: -1,
  animInterval: null,
  // Lightning
  lightningMap: null,
  lightningMarkers: [],       // [{marker, ts}] on the dedicated map
  radarLightningMarkers: [],  // [{marker, ts}] overlaid on radar map
  lightningOverlayActive: false,
  lightningWs: null,
  lightningStrikes: [],       // last 60 min of raw strikes
  lightningWsRetries: 0,
};

// ── DOM helpers ──────────────────────────────────────────────────────────────
const el = (id) => document.getElementById(id);
const setText = (id, val) => { const e = el(id); if (e) e.textContent = val ?? "--"; };
const setHTML = (id, val) => { const e = el(id); if (e) e.innerHTML = val; };

function setDot(id, status) {
  const d = el(id);
  if (!d) return;
  d.className = "refresh-dot " + (status || "loading");
}

function relativeTime(isoStr) {
  if (!isoStr) return "--";
  const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  return `${Math.floor(diff/3600)}h ago`;
}

function fmt(val, decimals = 1, fallback = "--") {
  if (val === null || val === undefined) return fallback;
  return Number(val).toFixed(decimals);
}

function nwsIconToEmoji(iconUrl, isDay) {
  if (!iconUrl) return isDay ? "🌤" : "🌙";
  const lower = iconUrl.toLowerCase();
  if (lower.includes("thunderstorm") || lower.includes("tsra")) return "⛈";
  if (lower.includes("tornado"))    return "🌪";
  if (lower.includes("hurricane"))  return "🌀";
  if (lower.includes("blizzard"))   return "🌨";
  if (lower.includes("snow"))       return "❄";
  if (lower.includes("sleet") || lower.includes("mix") || lower.includes("fzra")) return "🌨";
  if (lower.includes("rain") || lower.includes("showers") || lower.includes("drizzle")) return "🌧";
  if (lower.includes("fog"))        return "🌫";
  if (lower.includes("wind"))       return "💨";
  if (lower.includes("overcast") || lower.includes("bkn") || lower.includes("ovc")) return "☁";
  if (lower.includes("cloudy") || lower.includes("sct"))  return isDay ? "⛅" : "🌥";
  if (lower.includes("few"))        return isDay ? "🌤" : "🌙";
  if (lower.includes("clear") || lower.includes("skc")) return isDay ? "☀" : "🌙";
  if (lower.includes("sunny"))      return "☀";
  return isDay ? "🌤" : "🌙";
}

// ── Clock ────────────────────────────────────────────────────────────────────
function startClock() {
  const timeEl = el("clock");
  const dateEl = el("dateline");
  const days = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

  function tick() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2,"0");
    const m = String(now.getMinutes()).padStart(2,"0");
    const s = String(now.getSeconds()).padStart(2,"0");
    timeEl.textContent = `${h}:${m}:${s}`;
    dateEl.textContent = `${days[now.getDay()]}, ${months[now.getMonth()]} ${now.getDate()}`;
  }
  tick();
  setInterval(tick, 1000);
}

// ── Fetch wrapper ────────────────────────────────────────────────────────────
async function apiFetch(path) {
  try {
    const resp = await fetch(path, { headers: { "Accept": "application/json" } });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (e) {
    console.warn(`API fetch failed for ${path}:`, e);
    return { error: e.message };
  }
}

// ── Radar (RainViewer + Leaflet) ─────────────────────────────────────────────
function initRadar() {
  const map = L.map("radar-map", {
    center: [APP_CONFIG.lat, APP_CONFIG.lon],
    zoom: 7,
    zoomControl: true,
    attributionControl: true,
  });

  // Dark base tile
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CartoDB</a>',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(map);

  // Location marker
  L.circleMarker([APP_CONFIG.lat, APP_CONFIG.lon], {
    radius: 6,
    fillColor: "#3d8ef8",
    fillOpacity: 0.9,
    color: "#fff",
    weight: 1.5,
  }).addTo(map).bindPopup("Olympia, WA");

  state.map = map;
  loadRainViewerFrames();
}

async function loadRainViewerFrames() {
  setDot("radar-dot", "loading");
  const data = await apiFetch("/api/radar/times");

  if (data.error) {
    setDot("radar-dot", "error");
    el("radar-ts").textContent = "Radar unavailable";
    return;
  }

  const host = data.host;
  const colorScheme = 2;  // Meteorological
  const smooth = 1;
  const snow = 1;

  // Get past frames (radar) and future frames (forecast)
  const pastFrames = (data.radar?.past || []).slice(-8);
  const futureFrames = (data.radar?.nowcast || []).slice(0, 3);
  const satelliteFrames = data.satellite?.infrared || [];

  state.rainviewerFrames = {
    rain: pastFrames.map(f => ({
      url: `${host}${f.path}/512/{z}/{x}/{y}/${colorScheme}/${smooth}_${snow}.png`,
      time: f.time,
    })),
    snow: pastFrames.map(f => ({
      url: `${host}${f.path}/512/{z}/{x}/{y}/${colorScheme}/${smooth}_${snow}.png`,
      time: f.time,
    })),
    cloud: satelliteFrames.slice(-4).map(f => ({
      url: `${host}${f.path}/512/{z}/{x}/{y}/0/1_0.png`,
      time: f.time,
    })),
  };

  startRadarAnimation();
  setDot("radar-dot", "ok");

  const lastTime = pastFrames[pastFrames.length - 1]?.time;
  if (lastTime) {
    el("radar-ts").textContent = "Radar: " + new Date(lastTime * 1000).toLocaleTimeString([], {
      hour: "2-digit", minute: "2-digit"
    });
    el("radar-updated").textContent = relativeTime(new Date(lastTime * 1000).toISOString());
  }
}

function startRadarAnimation() {
  if (state.animInterval) clearInterval(state.animInterval);

  const frames = state.rainviewerFrames[state.radarLayer] || [];
  if (!frames.length) return;

  let idx = frames.length - 1;

  function showFrame(i) {
    if (state.rainviewerLayer) {
      state.map.removeLayer(state.rainviewerLayer);
    }
    const frame = frames[i];
    state.rainviewerLayer = L.tileLayer(frame.url, {
      opacity: 0.65,
      zIndex: 200,
    });
    state.rainviewerLayer.addTo(state.map);
    state.rainviewerCurrentFrame = i;

    // Update timestamp
    el("radar-ts").textContent = new Date(frame.time * 1000).toLocaleTimeString([], {
      hour: "2-digit", minute: "2-digit"
    }) + " radar";
  }

  showFrame(idx);
  state.animInterval = setInterval(() => {
    idx = (idx + 1) % frames.length;
    showFrame(idx);
  }, 800);
}

function setRadarLayer(layer) {
  state.radarLayer = layer;
  ["rain","snow","cloud"].forEach(l => {
    const btn = el(`btn-${l}`);
    if (btn) btn.classList.toggle("active", l === layer);
  });
  startRadarAnimation();
}

function toggleLightningLayer() {
  state.lightningOverlayActive = !state.lightningOverlayActive;
  const btn = el("btn-lightning");
  if (btn) btn.classList.toggle("active", state.lightningOverlayActive);
  if (state.lightningOverlayActive) {
    redrawRadarLightning();
  } else {
    state.radarLightningMarkers.forEach(m => state.map.removeLayer(m.marker));
    state.radarLightningMarkers = [];
  }
}

// ── Lightning (Blitzortung WebSocket) ────────────────────────────────────────

const LIGHTNING_COLORS = [
  { maxAge: 5 * 60,  color: "#fff700", radius: 5, opacity: 0.95 },
  { maxAge: 15 * 60, color: "#ff9500", radius: 4, opacity: 0.75 },
  { maxAge: 30 * 60, color: "#ff4444", radius: 3, opacity: 0.55 },
  { maxAge: 60 * 60, color: "#663333", radius: 2, opacity: 0.35 },
];

// Blitzortung uses multiple regional servers on ports 7654-7660.
// We try them in order and reconnect on failure.
const WS_PORTS = [7654, 7655, 7656, 7657, 7658, 7659, 7660];

function initLightningMap() {
  const container = el("lightning-map");
  if (!container) return;

  const lmap = L.map("lightning-map", {
    center: [APP_CONFIG.lat, APP_CONFIG.lon],
    zoom: 6,
    zoomControl: true,
    attributionControl: true,
  });

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; CartoDB | Lightning: Blitzortung.org',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(lmap);

  L.circleMarker([APP_CONFIG.lat, APP_CONFIG.lon], {
    radius: 5, fillColor: "#3d8ef8", fillOpacity: 0.9, color: "#fff", weight: 1.5,
  }).addTo(lmap);

  state.lightningMap = lmap;
  connectBlitzortung();
}

function connectBlitzortung() {
  const portIdx = state.lightningWsRetries % WS_PORTS.length;
  const port = WS_PORTS[portIdx];
  const wsUrl = `wss://ws.blitzortung.org:${port}/`;

  updateLightningStatus("Connecting…");
  setDot("lightning-dot", "loading");

  try {
    const ws = new WebSocket(wsUrl);
    state.lightningWs = ws;

    ws.onopen = () => {
      updateLightningStatus("Live — Blitzortung.org");
      setDot("lightning-dot", "ok");
      state.lightningWsRetries = 0;
      // Subscribe to region (broad North America + Pacific)
      ws.send(JSON.stringify({ west: -180, east: -60, north: 75, south: 20 }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.lat !== undefined && data.lon !== undefined) {
          onLightningStrike(data.lat, data.lon, data.time || Date.now() / 1000);
        }
      } catch (_) { /* ignore parse errors */ }
    };

    ws.onerror = () => {
      setDot("lightning-dot", "error");
    };

    ws.onclose = () => {
      // Reconnect with exponential backoff, cycling through ports
      state.lightningWsRetries++;
      const delay = Math.min(30000, 2000 * Math.pow(1.5, Math.min(state.lightningWsRetries, 8)));
      updateLightningStatus(`Reconnecting in ${Math.round(delay/1000)}s…`);
      setDot("lightning-dot", "stale");
      setTimeout(connectBlitzortung, delay);
    };
  } catch (e) {
    setDot("lightning-dot", "error");
    updateLightningStatus("WebSocket unavailable");
  }
}

function onLightningStrike(lat, lon, unixTime) {
  const nowSec = Date.now() / 1000;
  const ageSec = nowSec - unixTime;
  if (ageSec > 3600) return;  // ignore strikes older than 1 hour

  // Record strike
  state.lightningStrikes.push({ lat, lon, ts: unixTime });
  // Prune strikes older than 1 hour
  const cutoff = nowSec - 3600;
  state.lightningStrikes = state.lightningStrikes.filter(s => s.ts >= cutoff);

  // Update counter badge
  const badge = el("strike-count-badge");
  if (badge) {
    const recent = state.lightningStrikes.filter(s => s.ts >= nowSec - 3600).length;
    badge.textContent = `${recent} strikes / hr`;
    badge.style.display = "inline-block";
  }

  const style = _strikeStyle(ageSec);

  // Plot on dedicated lightning map
  if (state.lightningMap) {
    const m = L.circleMarker([lat, lon], {
      radius: style.radius,
      fillColor: style.color,
      fillOpacity: style.opacity,
      color: style.color,
      weight: 0,
      pane: "markerPane",
    }).addTo(state.lightningMap);
    state.lightningMarkers.push({ marker: m, ts: unixTime });
  }

  // Plot on radar map if overlay is active
  if (state.lightningOverlayActive && state.map) {
    const m = L.circleMarker([lat, lon], {
      radius: style.radius,
      fillColor: style.color,
      fillOpacity: style.opacity,
      color: style.color,
      weight: 0,
      zIndexOffset: 500,
    }).addTo(state.map);
    state.radarLightningMarkers.push({ marker: m, ts: unixTime });
  }
}

function _strikeStyle(ageSec) {
  for (const s of LIGHTNING_COLORS) {
    if (ageSec <= s.maxAge) return s;
  }
  return LIGHTNING_COLORS[LIGHTNING_COLORS.length - 1];
}

function redrawRadarLightning() {
  // Remove old radar markers
  state.radarLightningMarkers.forEach(m => state.map.removeLayer(m.marker));
  state.radarLightningMarkers = [];
  if (!state.lightningOverlayActive || !state.map) return;

  const nowSec = Date.now() / 1000;
  state.lightningStrikes.forEach(s => {
    const ageSec = nowSec - s.ts;
    const style = _strikeStyle(ageSec);
    const m = L.circleMarker([s.lat, s.lon], {
      radius: style.radius,
      fillColor: style.color,
      fillOpacity: style.opacity,
      color: style.color,
      weight: 0,
      zIndexOffset: 500,
    }).addTo(state.map);
    state.radarLightningMarkers.push({ marker: m, ts: s.ts });
  });
}

// Age out lightning markers periodically and refresh colors
function ageLightningMarkers() {
  const nowSec = Date.now() / 1000;
  const cutoff = nowSec - 3600;

  // Dedicated map
  if (state.lightningMap) {
    state.lightningMarkers = state.lightningMarkers.filter(m => {
      if (m.ts < cutoff) {
        state.lightningMap.removeLayer(m.marker);
        return false;
      }
      // Update color for aged strikes
      const style = _strikeStyle(nowSec - m.ts);
      m.marker.setStyle({ fillColor: style.color, color: style.color,
                          fillOpacity: style.opacity, radius: style.radius });
      return true;
    });
  }

  // Radar overlay
  if (state.lightningOverlayActive && state.map) {
    state.radarLightningMarkers = state.radarLightningMarkers.filter(m => {
      if (m.ts < cutoff) {
        state.map.removeLayer(m.marker);
        return false;
      }
      const style = _strikeStyle(nowSec - m.ts);
      m.marker.setStyle({ fillColor: style.color, color: style.color,
                          fillOpacity: style.opacity, radius: style.radius });
      return true;
    });
  }

  const recent = state.lightningStrikes.filter(s => s.ts >= nowSec - 3600).length;
  const badge = el("strike-count-badge");
  if (badge) {
    if (recent > 0) {
      badge.textContent = `${recent} / hr`;
      badge.style.display = "inline-block";
    } else {
      badge.style.display = "none";
    }
  }

  const ts = el("lightning-updated");
  if (ts) ts.textContent = `${recent} strikes`;
}

function updateLightningStatus(msg) {
  const s = el("lightning-status");
  if (s) s.textContent = msg;
  const ts = el("lightning-updated");
  if (ts) ts.textContent = msg;
}

// ── Current Conditions ───────────────────────────────────────────────────────
async function loadCurrentConditions() {
  setDot("wind-dot", "loading");
  setDot("precip-dot", "loading");

  const data = await apiFetch("/api/current");

  if (data.error) {
    setDot("wind-dot", "error");
    setDot("precip-dot", "error");
    return;
  }

  // Top bar
  setText("tb-temp", data.temperature_f != null ? `${fmt(data.temperature_f, 0)}°F` : "--");
  setText("tb-desc", data.description || "--");
  setText("tb-wind",
    data.wind_speed_mph != null
      ? `${fmt(data.wind_speed_mph, 0)} mph ${data.wind_direction_cardinal || ""}`
      : "--"
  );
  setText("tb-humidity", data.humidity != null ? `${fmt(data.humidity, 0)}%` : "--");
  setText("tb-pressure", data.pressure_inhg != null ? `${fmt(data.pressure_inhg, 2)}"` : "--");
  setText("tb-vis", data.visibility_miles != null ? `${fmt(data.visibility_miles, 1)} mi` : "--");

  // Wind card
  const speed = data.wind_speed_mph;
  const gust = data.wind_gust_mph;
  const dir = data.wind_direction_deg;
  const cardinal = data.wind_direction_cardinal;

  setText("wind-speed", speed != null ? fmt(speed, 0) : "--");
  setText("wind-dir", cardinal && dir != null ? `${cardinal} (${Math.round(dir)}°)` : (cardinal || "--"));
  setText("wind-gust", gust != null ? fmt(gust, 0) : "--");

  // Rotate compass arrow
  if (dir != null) {
    el("wind-arrow").setAttribute("transform", `rotate(${dir} 40 40)`);
  }

  const ts = data.timestamp;
  const timeAgo = ts ? relativeTime(ts) : "--";
  if (el("wind-updated")) el("wind-updated").textContent = timeAgo;

  setDot("wind-dot", "ok");

  // Precipitation (also comes from current)
  setText("precip-1h",  data.precip_1h_in  != null ? `${fmt(data.precip_1h_in, 2)}"` : "0.00\"");
  setText("precip-24h", data.precip_24h_in != null ? `${fmt(data.precip_24h_in, 2)}"` : "--");
  if (el("precip-updated")) el("precip-updated").textContent = timeAgo;
  setDot("precip-dot", "ok");
}

async function loadPrecipitation() {
  const data = await apiFetch("/api/precipitation");
  if (!data.error) {
    if (data.precip_1h_in  != null) setText("precip-1h",  `${fmt(data.precip_1h_in,  2)}"`);
    if (data.precip_24h_in != null) setText("precip-24h", `${fmt(data.precip_24h_in, 2)}"`);
    if (data.precip_7day_in != null) setText("precip-7d", `${fmt(data.precip_7day_in, 2)}"`);
    else setText("precip-7d", "--");
  }
}

// ── Alerts ───────────────────────────────────────────────────────────────────
const SEVERITY_COLOR = {
  Extreme:  ["extreme",  "#7f1d1d"],
  Severe:   ["severe",   "#991b1b"],
  Moderate: ["moderate", "#92400e"],
  Minor:    ["minor",    "#374151"],
  Unknown:  ["minor",    "#374151"],
};

function renderAlerts(alerts) {
  const banner = el("alert-banner");
  const scroller = el("alert-scroller");

  // Also filter for flood warnings
  const floodWarnings = alerts.filter(a =>
    a.event && (a.event.toLowerCase().includes("flood") || a.event.toLowerCase().includes("high surf"))
  );
  renderFloodWarnings(floodWarnings);

  if (!alerts.length) {
    banner.classList.remove("visible");
    return;
  }

  banner.classList.add("visible");
  scroller.innerHTML = alerts.map(a => {
    const [cls] = SEVERITY_COLOR[a.severity] || ["minor", "#374151"];
    const expires = a.expires ? new Date(a.expires).toLocaleString([], {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    }) : "";
    return `
      <div class="alert-item" onclick="showAlertModal(${JSON.stringify(a).replace(/"/g, '&quot;')})">
        <span class="alert-badge ${cls}">${a.severity}</span>
        <span class="alert-text">⚠ ${a.event} — ${a.headline || a.description?.slice(0,80) || ""}</span>
        ${expires ? `<span class="alert-time">until ${expires}</span>` : ""}
      </div>`;
  }).join("");
  state.alerts = alerts;
}

function renderFloodWarnings(warnings) {
  const card = el("flood-card");
  const body = el("flood-body");
  if (!warnings.length) {
    card.style.display = "none";
    return;
  }
  card.style.display = "block";
  body.innerHTML = warnings.map(w => `
    <div style="margin-bottom:0.6rem;padding:0.5rem;background:rgba(249,115,22,0.1);border-radius:6px;border:1px solid rgba(249,115,22,0.3)">
      <div style="font-size:0.78rem;font-weight:600;color:#fdba74">${w.event}</div>
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:0.2rem">${w.headline}</div>
      ${w.expires ? `<div style="font-size:0.65rem;color:#64748b;margin-top:0.15rem">Expires: ${new Date(w.expires).toLocaleString()}</div>` : ""}
    </div>`).join("");
}

async function loadAlerts() {
  const data = await apiFetch("/api/alerts");
  if (!data.error) {
    renderAlerts(data.alerts || []);
  }
}

// Alert Modal
function showAlertModal(alert) {
  el("modal-title").textContent = `⚠ ${alert.event}`;
  el("modal-meta").innerHTML = [
    `<span class="alert-meta-item">Severity: ${alert.severity}</span>`,
    `<span class="alert-meta-item">Urgency: ${alert.urgency}</span>`,
    `<span class="alert-meta-item">Certainty: ${alert.certainty}</span>`,
    alert.onset  ? `<span class="alert-meta-item">Onset: ${new Date(alert.onset).toLocaleString()}</span>` : "",
    alert.expires ? `<span class="alert-meta-item">Expires: ${new Date(alert.expires).toLocaleString()}</span>` : "",
    alert.area ? `<span class="alert-meta-item">Area: ${alert.area}</span>` : "",
  ].filter(Boolean).join("");

  const body = [alert.headline, "", alert.description, "", alert.instruction]
    .filter(s => s !== undefined && s !== null)
    .join("\n").trim();
  el("modal-body").textContent = body;
  el("alert-modal").classList.add("open");
}

function closeAlertModal(e) {
  if (!e || e.target === el("alert-modal")) {
    el("alert-modal").classList.remove("open");
  }
}

// ── Hourly Forecast ──────────────────────────────────────────────────────────
async function loadHourlyForecast() {
  setDot("hourly-dot", "loading");
  const data = await apiFetch("/api/forecast/hourly");

  if (data.error) {
    setDot("hourly-dot", "error");
    setHTML("hourly-list", `<div class="error-state"><span class="error-icon">📡</span>Forecast unavailable</div>`);
    return;
  }

  const now = new Date();
  const currentHour = now.getHours();

  const html = (data.periods || []).map((p, i) => {
    const dt = new Date(p.time);
    const h = dt.getHours();
    const isNow = i === 0;
    const timeLabel = isNow ? "Now" : dt.toLocaleTimeString([], {hour:"numeric"});
    const emoji = nwsIconToEmoji(p.icon, p.is_daytime);
    const precip = p.precip_chance != null ? `${Math.round(p.precip_chance)}%` : "";
    return `
      <div class="hourly-item ${isNow ? "current-hour" : ""}" title="${p.description}">
        <span class="hourly-time">${timeLabel}</span>
        <span class="hourly-icon">${emoji}</span>
        <span class="hourly-temp">${p.temp_f}°</span>
        ${precip ? `<span class="hourly-precip">${precip}</span>` : `<span class="hourly-precip" style="color:transparent">0%</span>`}
      </div>`;
  }).join("");

  setHTML("hourly-list", html);
  el("hourly-updated").textContent = relativeTime(new Date().toISOString());
  setDot("hourly-dot", "ok");
}

// ── Daily Forecast ───────────────────────────────────────────────────────────
async function loadDailyForecast() {
  setDot("daily-dot", "loading");
  const data = await apiFetch("/api/forecast/daily");

  if (data.error) {
    setDot("daily-dot", "error");
    setHTML("daily-list", `<div class="error-state"><span class="error-icon">📡</span>Forecast unavailable</div>`);
    return;
  }

  const html = (data.periods || []).map((p, i) => {
    const emoji = nwsIconToEmoji(p.icon, p.is_daytime);
    const dayName = i === 0 ? "Today" : (p.name || new Date(p.date).toLocaleDateString([], {weekday:"short"}));
    const hi = `${p.temp_f}°`;
    const lo = p.low_f != null ? `${p.low_f}°` : "";
    const precip = p.precip_chance != null ? ` · ${Math.round(p.precip_chance)}%🌧` : "";
    return `
      <div class="daily-item" title="${p.detailed || p.description}">
        <span class="daily-day">${dayName}</span>
        <span class="daily-icon">${emoji}</span>
        <span class="daily-desc">${p.description}${precip}</span>
        <span class="daily-temps">
          <span class="daily-high">${hi}</span>
          ${lo ? `<span class="daily-low">${lo}</span>` : ""}
        </span>
      </div>`;
  }).join("");

  setHTML("daily-list", html);
  el("daily-updated").textContent = relativeTime(new Date().toISOString());
  setDot("daily-dot", "ok");
}

// ── Sun Times ────────────────────────────────────────────────────────────────
async function loadSunTimes() {
  const data = await apiFetch("/api/sun");
  if (data.error) return;

  setText("sun-rise", data.sunrise);
  setText("sun-set", data.sunset);
  setText("sun-next", data.next_event);
  setText("sun-next-label", data.next_event_label);
  setText("sun-daylight", `${data.daylight_hours} hrs daylight`);

  const prog = data.day_progress || 0;
  el("sun-fill").style.width = `${prog}%`;
  el("sun-dot-el").style.left = `${Math.max(1, Math.min(99, prog))}%`;
  setDot("sun-dot", "ok");
}

// ── AQI ──────────────────────────────────────────────────────────────────────
async function loadAQI() {
  setDot("aqi-dot", "loading");
  const data = await apiFetch("/api/aqi");
  const display = el("aqi-display");

  if (!data.configured) {
    display.innerHTML = `
      <div class="aqi-unconfigured">
        Set <code>AIRNOW_API_KEY</code> in <code>.env</code> to enable AQI.
        <a href="https://docs.airnowapi.org/account/request/" target="_blank" rel="noopener"
           style="color:var(--accent)">Get free key →</a>
      </div>`;
    setText("tb-aqi", "N/A");
    setDot("aqi-dot", "unknown");
    return;
  }

  if (data.error && !data.aqi) {
    display.innerHTML = `<div class="error-state"><span class="error-icon">💨</span>AQI unavailable</div>`;
    setDot("aqi-dot", "error");
    return;
  }

  const bg = data.bg_color || "#444";
  const fg = data.text_color || "#fff";

  display.innerHTML = `
    <div class="aqi-badge" style="background:${bg};color:${fg}">
      <div class="aqi-number">${data.aqi ?? "--"}</div>
      <div class="aqi-cat">${data.category}</div>
    </div>
    <div>
      <div class="aqi-detail" style="color:${fg === '#fff' ? 'var(--text-secondary)' : 'var(--text-muted)'}">${data.category}</div>
      <div class="aqi-pollutant">Primary: ${data.primary_pollutant || "--"}</div>
      <div class="aqi-pollutant">Area: ${data.reporting_area || "--"}</div>
    </div>`;

  setText("tb-aqi", data.aqi != null ? String(data.aqi) : "--");
  el("tb-aqi").style.color = bg;

  el("aqi-updated").textContent = relativeTime(new Date().toISOString());
  setDot("aqi-dot", "ok");
}

// ── Snow ─────────────────────────────────────────────────────────────────────
async function loadSnow() {
  const data = await apiFetch("/api/snow");
  if (data.has_snow && data.snow_depth_in != null && data.snow_depth_in > 0) {
    el("snow-card").style.display = "block";
    setText("snow-depth", fmt(data.snow_depth_in, 1));
  } else {
    el("snow-card").style.display = "none";
  }
}

// ── Rivers ───────────────────────────────────────────────────────────────────
async function loadRivers() {
  setDot("river-dot", "loading");
  const data = await apiFetch("/api/rivers");

  if (data.error) {
    setDot("river-dot", "error");
    setHTML("river-body", `<div class="error-state"><span class="error-icon">🌊</span>River data unavailable</div>`);
    return;
  }

  const html = (data.gauges || []).map(g => {
    if (g.error) {
      return `<div class="river-gauge">
        <div class="river-name">${g.name}</div>
        <div style="font-size:0.7rem;color:var(--text-muted)">Data unavailable</div>
      </div>`;
    }

    const ht = g.gage_height_ft;
    const flood = g.flood_stage_ft || 20;
    const action = g.action_stage_ft || 10;
    const pct = ht != null ? Math.min(100, (ht / (flood * 1.3)) * 100) : 0;

    const ts = g.timestamp ? relativeTime(g.timestamp) : "--";

    return `
      <div class="river-gauge">
        <div class="river-name">
          ${g.name}
          <span class="river-status" style="background:${g.flood_color}22;color:${g.flood_color};border:1px solid ${g.flood_color}44">
            ${g.flood_status}
          </span>
        </div>
        <div class="river-stats">
          <span class="river-height">${ht != null ? fmt(ht, 2) : "--"}</span>
          <span class="river-unit">ft</span>
          ${g.discharge_cfs != null ? `<span class="river-cfs">${fmt(g.discharge_cfs, 0)} cfs</span>` : ""}
        </div>
        <div class="river-bar-wrap">
          <div class="river-bar" style="width:${pct}%;background:${g.flood_color}"></div>
        </div>
        <div class="river-stages">
          <span>Action: ${action}ft</span>
          <span>Flood: ${flood}ft</span>
          <span style="color:var(--text-muted)">${ts}</span>
        </div>
      </div>`;
  }).join("");

  setHTML("river-body", html);
  el("river-updated").textContent = relativeTime(new Date().toISOString());
  setDot("river-dot", "ok");
}

// ── Tides ────────────────────────────────────────────────────────────────────
async function loadTides() {
  setDot("tides-dot", "loading");
  const data = await apiFetch("/api/tides");

  if (data.error) {
    setDot("tides-dot", "error");
    setHTML("tides-body", `<div class="error-state"><span class="error-icon">🌊</span>Tide data unavailable</div>`);
    return;
  }

  const currentLevel = data.current_level_ft;
  const allTides = [...(data.tides_today || []), ...(data.tides_tomorrow || [])].slice(0, 6);

  const tidesHtml = allTides.map(t => {
    const dt = new Date(t.time);
    const isToday = new Date().toDateString() === dt.toDateString();
    const timeStr = dt.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
    const dayLabel = isToday ? "" : `<span style="font-size:0.6rem;color:var(--text-muted)"> tmrw</span>`;
    return `
      <div class="tide-item">
        <span class="tide-time">${timeStr}${dayLabel}</span>
        <span class="tide-type ${t.type.toLowerCase()}">${t.type}</span>
        <span class="tide-height">${fmt(t.height_ft, 2)} ft</span>
      </div>`;
  }).join("");

  const levelHtml = currentLevel != null ? `
    <div class="tides-current">
      <span class="tide-current-val">${fmt(currentLevel, 2)}</span>
      <span class="tide-current-unit"> ft MLLW</span>
    </div>` : "";

  setHTML("tides-body", levelHtml + `<div class="tide-list">${tidesHtml}</div>`);
  el("tides-updated").textContent = relativeTime(new Date().toISOString());
  setDot("tides-dot", "ok");
}

// ── Traffic Cameras ──────────────────────────────────────────────────────────
async function loadCameras() {
  setDot("cam-dot", "loading");
  const data = await apiFetch("/api/cameras");

  if (data.error) {
    setDot("cam-dot", "error");
    setHTML("cam-grid", `<div class="error-state" style="grid-column:1/-1"><span class="error-icon">📷</span>Camera data unavailable</div>`);
    return;
  }

  state.cameras = data.cameras || [];
  renderCameras();
}

function renderCameras() {
  const grid = el("cam-grid");
  const ts = new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});

  grid.innerHTML = state.cameras.map(cam => `
    <div class="cam-card" onclick="openLightbox(${cam.id})" title="${cam.label}">
      <img
        class="cam-img"
        src="${cam.proxy_url}?t=${Date.now()}"
        alt="${cam.label}"
        loading="lazy"
        onerror="this.parentElement.innerHTML='<div class=\\'cam-error\\'><span class=\\'cam-error-icon\\'>📷</span><span>${cam.label}</span><span style=\\'font-size:0.62rem\\'>Unavailable</span></div>';this.parentElement.style.aspectRatio='16/9';"
      >
      <div class="cam-label">
        <strong>${cam.label}</strong>
        <span>${cam.location}</span>
      </div>
      <div class="cam-timestamp">${ts}</div>
    </div>`).join("");

  el("cam-updated").textContent = relativeTime(new Date().toISOString());
  setDot("cam-dot", "ok");
}

function openLightbox(camId) {
  const cam = state.cameras.find(c => c.id === camId);
  if (!cam) return;
  const img = el("lightbox-img");
  img.src = `${cam.proxy_url}?t=${Date.now()}`;
  img.alt = cam.label;
  el("lightbox-caption").textContent = `${cam.label} — ${cam.location}`;
  el("lightbox").classList.add("open");
}

function closeLightbox() {
  el("lightbox").classList.remove("open");
  el("lightbox-img").src = "";
}

document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    closeLightbox();
    closeAlertModal();
  }
});

// ── Health Check ─────────────────────────────────────────────────────────────
async function loadHealth() {
  setDot("health-dot", "loading");
  const data = await apiFetch("/api/health");

  if (data.error) {
    setDot("health-dot", "error");
    return;
  }

  const grid = el("health-grid");
  grid.innerHTML = (data.services || []).map(s => {
    const dotClass = s.status === "ok" ? "ok" : "error";
    const latency = s.latency_ms != null ? `${s.latency_ms}ms` : (s.cached ? "cached" : "");
    return `
      <div class="health-item" title="${s.detail || s.name}">
        <span class="health-name">${s.name}</span>
        <div class="health-right">
          <span class="health-latency">${latency}</span>
          <span class="health-dot ${dotClass}"></span>
        </div>
      </div>`;
  }).join("");

  el("health-updated").textContent = relativeTime(new Date().toISOString());
  setDot("health-dot", data.status === "ok" ? "ok" : "stale");
}

// ── Scheduler ────────────────────────────────────────────────────────────────
function scheduleRefresh(fn, intervalMs, runImmediately = false) {
  if (runImmediately) fn();
  setInterval(fn, intervalMs);
}

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  startClock();
  initRadar();
  initLightningMap();

  // Initial loads — stagger slightly to avoid hammering the server
  setTimeout(() => loadCurrentConditions(), 100);
  setTimeout(() => loadAlerts(), 200);
  setTimeout(() => loadHourlyForecast(), 300);
  setTimeout(() => loadDailyForecast(), 400);
  setTimeout(() => loadSunTimes(), 500);
  setTimeout(() => loadAQI(), 600);
  setTimeout(() => loadRivers(), 700);
  setTimeout(() => loadTides(), 800);
  setTimeout(() => loadCameras(), 900);
  setTimeout(() => loadHealth(), 1200);
  setTimeout(() => loadPrecipitation(), 1400);
  setTimeout(() => loadSnow(), 1500);

  // Scheduled refreshes (in milliseconds)
  scheduleRefresh(loadRainViewerFrames,     5 * 60 * 1000);   // Radar: 5 min
  scheduleRefresh(loadCurrentConditions,   10 * 60 * 1000);   // Current: 10 min
  scheduleRefresh(loadPrecipitation,       10 * 60 * 1000);
  scheduleRefresh(loadAlerts,               2 * 60 * 1000);   // Alerts: 2 min
  scheduleRefresh(loadHourlyForecast,      30 * 60 * 1000);   // Hourly: 30 min
  scheduleRefresh(loadDailyForecast,       30 * 60 * 1000);   // Daily: 30 min
  scheduleRefresh(loadAQI,                 30 * 60 * 1000);   // AQI: 30 min
  scheduleRefresh(loadRivers,              15 * 60 * 1000);   // Rivers: 15 min
  scheduleRefresh(loadTides,               30 * 60 * 1000);   // Tides: 30 min
  scheduleRefresh(renderCameras,           60 * 1000);        // Camera refresh: 60 sec
  scheduleRefresh(loadHealth,              60 * 1000);        // Health: 60 sec
  scheduleRefresh(loadSunTimes,            12 * 60 * 60 * 1000); // Sun: 12 hr
  scheduleRefresh(loadSnow,               30 * 60 * 1000);
  // Lightning marker aging — every 60 seconds
  setInterval(ageLightningMarkers, 60 * 1000);
});
