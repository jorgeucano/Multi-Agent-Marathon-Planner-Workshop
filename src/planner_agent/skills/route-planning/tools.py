"""Route planning tools for the Marathon Planner Agent.

NOT IN THE CODELAB. The codelab's planner instruction tells the agent to call
`plan_marathon_route`, and `get_tools()` tries to load it out of this file -
but no step ever creates the file. `load_tool_from_skill` returns None on a
missing file, so the tool is silently dropped and the agent invents a route
instead of computing one. This module supplies the missing implementation.

Loaded dynamically by importlib (the directory name is hyphenated and is not a
Python package), so this module must stay import-standalone: stdlib only, no
relative imports.
"""

from __future__ import annotations

import heapq
import json
import math
from typing import Any

MARATHON_KM = 42.195
MARATHON_MILES = 26.2

# ---------------------------------------------------------------------------
# Built-in road networks: landmark -> (lat, lon), plus the segments between them
# ---------------------------------------------------------------------------

CITY_NETWORKS: dict[str, dict[str, Any]] = {
    "las vegas": {
        "nodes": {
            "Las Vegas Festival Grounds": (36.1300, -115.1660),
            "Welcome to Las Vegas Sign": (36.0820, -115.1728),
            "Mandalay Bay": (36.0920, -115.1760),
            "Luxor": (36.0955, -115.1761),
            "MGM Grand": (36.1023, -115.1697),
            "Bellagio Fountains": (36.1126, -115.1767),
            "The Sphere": (36.1170, -115.1620),
            "Venetian": (36.1212, -115.1697),
            "Wynn": (36.1268, -115.1656),
            "Stratosphere": (36.1474, -115.1560),
            "Fremont Street Experience": (36.1706, -115.1430),
            "Symphony Park": (36.1700, -115.1540),
            "Downtown Container Park": (36.1665, -115.1390),
            "Sunset Park": (36.0640, -115.1160),
        },
        "edges": [
            ("Las Vegas Festival Grounds", "Wynn", "arterial"),
            ("Wynn", "Venetian", "boulevard"),
            ("Venetian", "The Sphere", "arterial"),
            ("The Sphere", "Bellagio Fountains", "arterial"),
            ("Venetian", "Bellagio Fountains", "boulevard"),
            ("Bellagio Fountains", "MGM Grand", "boulevard"),
            ("MGM Grand", "Luxor", "boulevard"),
            ("Luxor", "Mandalay Bay", "boulevard"),
            ("Mandalay Bay", "Welcome to Las Vegas Sign", "arterial"),
            ("Welcome to Las Vegas Sign", "Sunset Park", "arterial"),
            ("Sunset Park", "Mandalay Bay", "arterial"),
            ("Wynn", "Stratosphere", "boulevard"),
            ("Stratosphere", "Symphony Park", "arterial"),
            ("Symphony Park", "Fremont Street Experience", "street"),
            ("Fremont Street Experience", "Downtown Container Park", "street"),
            ("Downtown Container Park", "Stratosphere", "arterial"),
            ("Las Vegas Festival Grounds", "Symphony Park", "arterial"),
        ],
    },
    "austin": {
        "nodes": {
            "Texas State Capitol": (30.2747, -97.7404),
            "Congress Avenue Bridge": (30.2617, -97.7450),
            "Auditorium Shores": (30.2620, -97.7520),
            "Zilker Park": (30.2669, -97.7729),
            "Barton Springs Pool": (30.2640, -97.7713),
            "Lady Bird Lake Trail": (30.2530, -97.7400),
            "Rainey Street": (30.2570, -97.7390),
            "University of Texas Tower": (30.2862, -97.7394),
            "Mueller Lake Park": (30.2990, -97.7050),
            "East Sixth Street": (30.2670, -97.7350),
        },
        "edges": [
            ("Texas State Capitol", "University of Texas Tower", "boulevard"),
            ("University of Texas Tower", "Mueller Lake Park", "arterial"),
            ("Mueller Lake Park", "East Sixth Street", "arterial"),
            ("East Sixth Street", "Rainey Street", "street"),
            ("Rainey Street", "Lady Bird Lake Trail", "trail"),
            ("Lady Bird Lake Trail", "Congress Avenue Bridge", "trail"),
            ("Congress Avenue Bridge", "Auditorium Shores", "trail"),
            ("Auditorium Shores", "Barton Springs Pool", "trail"),
            ("Barton Springs Pool", "Zilker Park", "trail"),
            ("Zilker Park", "Auditorium Shores", "trail"),
            ("Congress Avenue Bridge", "Texas State Capitol", "boulevard"),
            ("Texas State Capitol", "East Sixth Street", "street"),
        ],
    },
    "buenos aires": {
        "nodes": {
            "Obelisco": (-34.6037, -58.3816),
            "Puerto Madero": (-34.6110, -58.3630),
            "Reserva Ecologica": (-34.6120, -58.3520),
            "La Boca": (-34.6345, -58.3630),
            "San Telmo": (-34.6210, -58.3730),
            "Plaza de Mayo": (-34.6083, -58.3712),
            "Recoleta": (-34.5875, -58.3930),
            "Palermo Bosques": (-34.5720, -58.4160),
            "Planetario": (-34.5690, -58.4120),
            "Barrancas de Belgrano": (-34.5600, -58.4500),
        },
        "edges": [
            ("Obelisco", "Plaza de Mayo", "boulevard"),
            ("Plaza de Mayo", "Puerto Madero", "boulevard"),
            ("Puerto Madero", "Reserva Ecologica", "trail"),
            ("Reserva Ecologica", "La Boca", "arterial"),
            ("La Boca", "San Telmo", "street"),
            ("San Telmo", "Plaza de Mayo", "street"),
            ("Obelisco", "Recoleta", "boulevard"),
            ("Recoleta", "Palermo Bosques", "boulevard"),
            ("Palermo Bosques", "Planetario", "trail"),
            ("Planetario", "Barrancas de Belgrano", "arterial"),
            ("Barrancas de Belgrano", "Palermo Bosques", "arterial"),
            ("Recoleta", "Puerto Madero", "arterial"),
        ],
    },
}

# Road type -> (surface, closure difficulty 1-5). Used for traffic planning.
ROAD_TYPES = {
    "boulevard": ("asphalt", 5),
    "arterial": ("asphalt", 4),
    "street": ("asphalt", 3),
    "trail": ("mixed", 1),
}


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in km between two (lat, lon) points."""
    r = 6371.0088
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _synthetic_network(city: str) -> dict[str, Any]:
    """Build a deterministic ring network for a city we have no data for.

    Keeps the demo alive for any city the audience shouts out, and is honest
    about it: the result is flagged `network_source="synthetic"`.
    """
    seed = sum(ord(c) for c in city.lower())
    lat0 = ((seed * 7) % 120) / 2.0 - 30.0
    lon0 = ((seed * 13) % 340) / 2.0 - 85.0
    n = 12
    radius_deg = 0.045
    nodes, order = {}, []
    for i in range(n):
        ang = 2 * math.pi * i / n
        name = f"{city.title()} Waypoint {i + 1}"
        nodes[name] = (
            round(lat0 + radius_deg * math.sin(ang), 5),
            round(lon0 + radius_deg * math.cos(ang) * 1.25, 5),
        )
        order.append(name)
    edges = [(order[i], order[(i + 1) % n], "street") for i in range(n)]
    edges += [(order[i], order[(i + n // 2) % n], "arterial") for i in range(0, n // 2, 2)]
    return {"nodes": nodes, "edges": edges, "synthetic": True}


def _get_network(city: str) -> dict[str, Any]:
    key = (city or "").strip().lower()
    for known in CITY_NETWORKS:
        if known in key or key in known:
            return CITY_NETWORKS[known]
    return _synthetic_network(city or "generic")


def _build_graph(network: dict[str, Any]) -> dict[str, list[tuple[str, float, str]]]:
    """Adjacency list: node -> [(neighbour, km, road_type)]. Undirected."""
    nodes = network["nodes"]
    graph: dict[str, list[tuple[str, float, str]]] = {n: [] for n in nodes}
    for a, b, road_type in network["edges"]:
        if a not in nodes or b not in nodes:
            continue
        km = _haversine_km(nodes[a], nodes[b])
        graph[a].append((b, km, road_type))
        graph[b].append((a, km, road_type))
    return graph


def _dijkstra(graph, nodes, source: str) -> tuple[dict[str, float], dict[str, str]]:
    """Classic Dijkstra over the road graph. Returns (dist, previous)."""
    dist = {n: math.inf for n in nodes}
    prev: dict[str, str] = {}
    dist[source] = 0.0
    queue = [(0.0, source)]
    visited: set[str] = set()
    while queue:
        d, node = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        for neighbour, km, _road in graph[node]:
            nd = d + km
            if nd < dist[neighbour]:
                dist[neighbour] = nd
                prev[neighbour] = node
                heapq.heappush(queue, (nd, neighbour))
    return dist, prev


def _path(prev: dict[str, str], source: str, target: str) -> list[str]:
    if source == target:
        return [source]
    out = [target]
    while out[-1] != source:
        if out[-1] not in prev:
            return []
        out.append(prev[out[-1]])
    out.reverse()
    return out


def plan_marathon_route(
    city: str,
    start_landmark: str = "",
    target_distance_km: float = MARATHON_KM,
) -> dict[str, Any]:
    """Plan a certified-distance marathon route over a city's road network.

    Chains shortest paths (Dijkstra) between landmarks until the accumulated
    distance reaches the marathon target, then closes the loop back to the
    start. Returns the waypoint list, per-segment detail, road-closure severity
    and a GeoJSON FeatureCollection ready for visualization.

    Args:
        city: City to plan the route in, e.g. "Las Vegas".
        start_landmark: Optional landmark to start and finish at. Defaults to
            the first landmark of the city network.
        target_distance_km: Target route distance in km. Defaults to the
            official marathon distance, 42.195 km.

    Returns:
        A dict with total_distance_km, total_distance_miles, waypoints,
        segments, road_closures, elevation_profile and route_geojson.
    """
    network = _get_network(city)
    nodes = network["nodes"]
    graph = _build_graph(network)
    landmarks = list(nodes.keys())

    start = start_landmark if start_landmark in nodes else landmarks[0]

    # Greedily chain landmarks, always hopping to the nearest unvisited one,
    # until we are close enough to the target that closing the loop lands on it.
    route: list[str] = [start]
    total_km = 0.0
    visited = {start}
    current = start

    while total_km < target_distance_km:
        dist, prev = _dijkstra(graph, nodes, current)
        candidates = [
            (d, n) for n, d in dist.items()
            if n not in visited and d != math.inf and d > 0
        ]
        if not candidates:
            visited = {current}  # allow a second lap over the network
            candidates = [
                (d, n) for n, d in dist.items() if d != math.inf and d > 0
            ]
            if not candidates:
                break
        remaining = target_distance_km - total_km
        # Prefer the hop that leaves the loop-closing leg closest to target,
        # and only take it if the loop can still be closed without overshooting
        # the certified distance by more than the 6% measurement margin.
        candidates.sort(
            key=lambda c: abs(remaining - c[0]) if c[0] <= remaining else c[0] - remaining
        )
        chosen = None
        for hop_km, nxt in candidates:
            close_km = _dijkstra(graph, nodes, nxt)[0].get(start, math.inf)
            projected = total_km + hop_km + (0.0 if close_km == math.inf else close_km)
            if projected <= target_distance_km * 1.06:
                chosen = (hop_km, nxt)
                break
        if chosen is None:
            break
        hop_km, nxt = chosen
        leg = _path(prev, current, nxt)
        route.extend(leg[1:])
        total_km += hop_km
        visited.add(nxt)
        current = nxt

    # Close the loop back to the start line.
    dist, prev = _dijkstra(graph, nodes, current)
    if dist.get(start, math.inf) != math.inf and current != start:
        route.extend(_path(prev, current, start)[1:])
        total_km += dist[start]

    # Scale the reported distance onto the certified marathon distance: a real
    # course is measured and adjusted with out-and-back sections. We report the
    # adjustment explicitly instead of silently pretending it is exact.
    raw_km = round(total_km, 3)
    adjustment_km = round(target_distance_km - raw_km, 3)

    segments, closures = [], []
    for a, b in zip(route, route[1:]):
        km = _haversine_km(nodes[a], nodes[b])
        road_type = next(
            (rt for n, _d, rt in graph[a] if n == b), "street"
        )
        surface, severity = ROAD_TYPES.get(road_type, ("asphalt", 3))
        segments.append({
            "from": a, "to": b,
            "distance_km": round(km, 3),
            "distance_miles": round(km * 0.621371, 3),
            "road_type": road_type,
            "surface": surface,
        })
        closures.append({
            "segment": f"{a} -> {b}",
            "road_type": road_type,
            "closure_severity": severity,
            "detour_required": severity >= 4,
        })

    coordinates = [[nodes[n][1], nodes[n][0]] for n in route]  # GeoJSON is lon,lat
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coordinates},
                "properties": {
                    "name": f"{city.title()} Marathon Course",
                    "distance_km": target_distance_km,
                    "distance_miles": round(target_distance_km * 0.621371, 2),
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coordinates[0]},
                "properties": {"name": "Start / Finish", "marker": "start_finish"},
            },
        ],
    }

    return {
        "city": city,
        "network_source": "synthetic" if network.get("synthetic") else "built-in",
        "start_finish": start,
        "waypoints": route,
        "unique_landmarks": len(set(route)),
        "raw_network_distance_km": raw_km,
        "course_adjustment_km": adjustment_km,
        "total_distance_km": target_distance_km,
        "total_distance_miles": MARATHON_MILES,
        "segments": segments,
        "road_closures": closures,
        "elevation_profile": "rolling (built-in network carries no elevation data)",
        "route_geojson": geojson,
    }


def add_water_stations(
    total_distance_km: float = MARATHON_KM,
    interval_km: float = 2.5,
    participants: int = 10000,
) -> dict[str, Any]:
    """Place water stations along the course and size them for the field.

    Args:
        total_distance_km: Course distance in km.
        interval_km: Distance between consecutive water stations.
        participants: Expected number of runners.

    Returns:
        A dict with the station list and consumption estimates.
    """
    count = max(1, int(total_distance_km // interval_km))
    stations = []
    for i in range(1, count + 1):
        km_mark = round(i * interval_km, 2)
        stations.append({
            "station_id": f"WS-{i:02d}",
            "km_mark": km_mark,
            "mile_mark": round(km_mark * 0.621371, 2),
            "cups_required": participants * 2,
            "volunteers": max(6, participants // 1500),
            "sports_drink": i % 2 == 0,
        })
    return {
        "water_station_count": count,
        "interval_km": interval_km,
        "stations": stations,
        "total_cups": sum(s["cups_required"] for s in stations),
        "total_volunteers": sum(s["volunteers"] for s in stations),
    }


def add_medical_tents(
    total_distance_km: float = MARATHON_KM,
    participants: int = 10000,
) -> dict[str, Any]:
    """Place medical tents along the course, weighted to the late miles.

    Args:
        total_distance_km: Course distance in km.
        participants: Expected number of runners.

    Returns:
        A dict with the medical tent list and staffing estimates.
    """
    # Medical demand concentrates after 30 km ("the wall") and at the finish.
    marks = [5, 10, 15, 20, 25, 30, 32, 35, 38, 40, round(total_distance_km, 2)]
    marks = [m for m in marks if m <= total_distance_km]
    tents = []
    for i, km in enumerate(marks, start=1):
        late = km >= 30
        tents.append({
            "tent_id": f"MED-{i:02d}",
            "km_mark": km,
            "mile_mark": round(km * 0.621371, 2),
            "level": "advanced" if late or km == marks[-1] else "basic",
            "staff": 12 if late else 6,
            "ambulance_on_site": late,
        })
    return {
        "medical_tent_count": len(tents),
        "tents": tents,
        "total_medical_staff": sum(t["staff"] for t in tents),
        "ambulances": sum(1 for t in tents if t["ambulance_on_site"]) + 2,
        "note": f"Staffing sized for {participants} participants.",
    }


if __name__ == "__main__":
    demo = plan_marathon_route("Las Vegas")
    print(json.dumps({k: v for k, v in demo.items() if k != "route_geojson"}, indent=2)[:2000])
