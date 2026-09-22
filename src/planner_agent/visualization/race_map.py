"""Animated, map-based race visualization for the workshop.

This is intentionally smaller than the keynote's Angular/Three.js frontend. It
uses the same deterministic route data produced by ``plan_marathon_route`` and
runs entirely in a notebook output, with no gateway, Redis, or API key.
"""

from __future__ import annotations

import json
from typing import Any

import folium
from branca.element import MacroElement, Template


ESRI_TILES = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
)


def _position_on_route(latlon: list[list[float]], fraction: float) -> list[float]:
    """Return a stable approximate position along a polyline."""
    if not latlon:
        raise ValueError("The route has no coordinates")
    fraction = min(1.0, max(0.0, fraction))
    scaled = fraction * (len(latlon) - 1)
    index = min(int(scaled), len(latlon) - 2)
    local = scaled - index
    a, b = latlon[index], latlon[index + 1]
    return [a[0] + (b[0] - a[0]) * local, a[1] + (b[1] - a[1]) * local]


class _RunnerAnimation(MacroElement):
    """Folium element that adds controls and animated runner markers."""

    def __init__(self, latlon: list[list[float]], runner_count: int, participants: int):
        super().__init__()
        self._name = "RunnerAnimation"
        route_json = json.dumps(latlon, separators=(",", ":"))
        runner_count = max(12, min(int(runner_count), 180))
        participants = max(1, int(participants))

        source = r"""
{% macro script(this, kwargs) %}
(function () {
  const map = {{ this._parent.get_name() }};
  const route = __ROUTE__;
  const runnerCount = __RUNNER_COUNT__;
  const participants = __PARTICIPANTS__;
  const durationMs = 90000;
  let playing = true;
  let speed = 1;
  let elapsed = 0;
  let previous = performance.now();

  function routePoint(progress) {
    const p = Math.max(0, Math.min(0.999999, progress));
    const scaled = p * (route.length - 1);
    const i = Math.min(Math.floor(scaled), route.length - 2);
    const t = scaled - i;
    return [
      route[i][0] + (route[i + 1][0] - route[i][0]) * t,
      route[i][1] + (route[i + 1][1] - route[i][1]) * t,
    ];
  }

  const colors = ['#00d4ff', '#ffca28', '#ff7043', '#7c4dff', '#26d07c'];
  const runners = [];
  for (let i = 0; i < runnerCount; i += 1) {
    const marker = L.circleMarker(route[0], {
      radius: i < 8 ? 4.2 : 2.8,
      color: '#07131f',
      weight: 0.7,
      fillColor: colors[i % colors.length],
      fillOpacity: 0.92,
      interactive: false,
      pane: 'markerPane',
    }).addTo(map);
    runners.push({
      marker,
      delay: (i / runnerCount) * 0.17,
      pace: 0.84 + ((i * 37) % 31) / 100,
      lane: ((i % 7) - 3) * 0.000025,
    });
  }

  const panel = L.control({position: 'topright'});
  panel.onAdd = function () {
    const el = L.DomUtil.create('div', 'race-control');
    el.innerHTML = `
      <div class="race-kicker">LIVE COURSE</div>
      <div class="race-title">Buenos Aires 42K</div>
      <div class="race-stats">
        <span><b id="race-km">0.0</b> km líder</span>
        <span><b id="race-clock">00:00</b> carrera</span>
      </div>
      <div class="race-note">${runnerCount} corredores visuales representan ${participants.toLocaleString('es-AR')}</div>
      <div class="race-actions">
        <button id="race-toggle">Pausar</button>
        <button data-speed="1" class="active">1×</button>
        <button data-speed="2">2×</button>
        <button data-speed="4">4×</button>
        <button id="race-reset">Reiniciar</button>
      </div>`;
    L.DomEvent.disableClickPropagation(el);
    return el;
  };
  panel.addTo(map);

  const css = document.createElement('style');
  css.textContent = `
    .race-control{background:#07131fee;color:#fff;padding:14px 16px;border:1px solid #ffffff26;
      border-radius:14px;box-shadow:0 14px 36px #00101e66;min-width:260px;font:13px/1.35 system-ui,sans-serif}
    .race-kicker{color:#00d4ff;font-size:10px;font-weight:800;letter-spacing:.18em}
    .race-title{font-size:20px;font-weight:800;margin:3px 0 10px}.race-stats{display:flex;gap:16px}
    .race-stats b{font-size:18px;color:#ffca28}.race-note{color:#b8c7d4;font-size:11px;margin:7px 0 10px}
    .race-actions{display:flex;gap:5px}.race-actions button{cursor:pointer;border:1px solid #ffffff30;
      border-radius:7px;background:#ffffff12;color:#fff;padding:5px 8px;font-weight:700}
    .race-actions button:hover,.race-actions button.active{background:#00d4ff;color:#07131f}
    .leaflet-container{background:#081723}.runner-legend{background:#07131fee!important;color:white!important}
  `;
  document.head.appendChild(css);

  const toggle = panel.getContainer().querySelector('#race-toggle');
  const reset = panel.getContainer().querySelector('#race-reset');
  const speedButtons = panel.getContainer().querySelectorAll('[data-speed]');
  toggle.onclick = () => { playing = !playing; toggle.textContent = playing ? 'Pausar' : 'Continuar'; };
  reset.onclick = () => { elapsed = 0; playing = true; toggle.textContent = 'Pausar'; };
  speedButtons.forEach((button) => {
    button.onclick = () => {
      speed = Number(button.dataset.speed);
      speedButtons.forEach((candidate) => candidate.classList.toggle('active', candidate === button));
    };
  });

  function render(now) {
    if (playing) elapsed += (now - previous) * speed;
    previous = now;
    const leaderProgress = Math.min(1, elapsed / durationMs);
    runners.forEach((runner) => {
      const progress = Math.max(0, Math.min(1, (elapsed / durationMs) * runner.pace - runner.delay));
      const point = routePoint(progress);
      point[0] += runner.lane;
      point[1] -= runner.lane;
      runner.marker.setLatLng(point);
      runner.marker.setStyle({fillOpacity: progress >= 1 ? 0.25 : 0.92});
    });
    panel.getContainer().querySelector('#race-km').textContent = (leaderProgress * 42.195).toFixed(1);
    const raceMinutes = Math.floor(leaderProgress * 240);
    panel.getContainer().querySelector('#race-clock').textContent =
      String(Math.floor(raceMinutes / 60)).padStart(2, '0') + ':' + String(raceMinutes % 60).padStart(2, '0');
    if (leaderProgress >= 1) { playing = false; toggle.textContent = 'Finalizada'; }
    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);
})();
{% endmacro %}
"""
        source = source.replace("__ROUTE__", route_json)
        source = source.replace("__RUNNER_COUNT__", str(runner_count))
        source = source.replace("__PARTICIPANTS__", str(participants))
        self._template = Template(source)


def build_animated_race_map(
    route: dict[str, Any],
    water: dict[str, Any],
    medical: dict[str, Any],
    *,
    participants: int = 30_000,
    runner_count: int = 120,
) -> folium.Map:
    """Build an animated Folium map from the planner's deterministic outputs."""
    features = route.get("route_geojson", {}).get("features", [])
    if not features:
        raise ValueError("route_geojson does not contain a route feature")
    coordinates = features[0].get("geometry", {}).get("coordinates", [])
    if len(coordinates) < 2:
        raise ValueError("The route needs at least two coordinates")
    latlon = [[float(lonlat[1]), float(lonlat[0])] for lonlat in coordinates]

    race_map = folium.Map(
        location=latlon[0],
        zoom_start=13,
        tiles=ESRI_TILES,
        attr="Tiles &copy; Esri",
        control_scale=True,
        prefer_canvas=True,
    )
    folium.PolyLine(latlon, weight=12, opacity=0.28, color="#07131f").add_to(race_map)
    folium.PolyLine(
        latlon,
        weight=6,
        opacity=0.95,
        color="#ff5a36",
        tooltip="26.2 miles (42.195 km)",
    ).add_to(race_map)

    folium.Marker(
        latlon[0],
        tooltip=f"Largada / llegada: {route.get('start_finish', 'Obelisco')}",
        icon=folium.Icon(color="green", icon="flag"),
    ).add_to(race_map)

    seen: set[str] = set()
    for index, name in enumerate(route.get("waypoints", [])):
        if name in seen or index >= len(latlon):
            continue
        seen.add(name)
        folium.CircleMarker(
            latlon[index], radius=4, color="#ffffff", weight=1,
            fill=True, fill_color="#ff5a36", fill_opacity=1,
            tooltip=name,
        ).add_to(race_map)

    distance = float(route.get("total_distance_km") or 42.195)
    for station in water.get("stations", []):
        position = _position_on_route(latlon, float(station["km_mark"]) / distance)
        folium.CircleMarker(
            position, radius=5, color="#e7fbff", weight=1,
            fill=True, fill_color="#00a9e8", fill_opacity=0.95,
            tooltip=f"Agua {station['station_id']} · km {station['km_mark']}",
        ).add_to(race_map)

    for tent in medical.get("tents", []):
        position = _position_on_route(latlon, float(tent["km_mark"]) / distance)
        folium.Marker(
            position,
            tooltip=f"Médico {tent['tent_id']} · km {tent['km_mark']}",
            icon=folium.DivIcon(html=(
                '<div style="width:18px;height:18px;border-radius:5px;background:#e53935;'
                'color:white;font:bold 14px/18px system-ui;text-align:center;box-shadow:0 1px 4px #0008">+</div>'
            )),
        ).add_to(race_map)

    race_map.fit_bounds(latlon, padding=(24, 24))
    race_map.add_child(_RunnerAnimation(latlon, runner_count, participants))
    return race_map
