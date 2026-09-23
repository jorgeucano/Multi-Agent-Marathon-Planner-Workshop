"""Tests for the route-planning skill. Pure stdlib - no GCP, no network."""

import importlib.util
import pathlib

import pytest

TOOLS = (
    pathlib.Path(__file__).resolve().parent.parent
    / "src/planner_agent/skills/route-planning/tools.py"
)


def load_route_tools():
    spec = importlib.util.spec_from_file_location("route_tools", TOOLS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rt():
    return load_route_tools()


def test_skill_tools_file_exists():
    """The codelab's get_tools() silently drops the tool if this file is gone."""
    assert TOOLS.exists(), f"missing {TOOLS}"


@pytest.mark.parametrize("city", ["Las Vegas", "Austin", "Buenos Aires"])
def test_builtin_cities_produce_a_certified_course(rt, city):
    route = rt.plan_marathon_route(city)
    assert route["network_source"] == "built-in"
    assert route["total_distance_km"] == pytest.approx(42.195)
    assert route["total_distance_miles"] == pytest.approx(26.2)
    # The raw network loop must land near the target, not be scaled from nothing.
    assert abs(route["raw_network_distance_km"] - 42.195) < 5.0
    assert route["waypoints"][0] == route["waypoints"][-1], "course must be a loop"
    assert len(route["segments"]) == len(route["waypoints"]) - 1


def test_unknown_city_falls_back_without_crashing(rt):
    route = rt.plan_marathon_route("Ulaanbaatar")
    assert route["network_source"] == "synthetic"
    assert abs(route["raw_network_distance_km"] - 42.195) < 8.0


def test_geojson_is_wellformed(rt):
    gj = rt.plan_marathon_route("Las Vegas")["route_geojson"]
    assert gj["type"] == "FeatureCollection"
    line = gj["features"][0]
    assert line["geometry"]["type"] == "LineString"
    for lon, lat in line["geometry"]["coordinates"]:
        assert -180 <= lon <= 180, "GeoJSON is lon,lat - not lat,lon"
        assert -90 <= lat <= 90


def test_buenos_aires_is_a_single_direction_scenic_loop(rt):
    route = rt.plan_marathon_route("Buenos Aires", start_landmark="Obelisco")
    middle = route["waypoints"][:-1]

    assert route["waypoints"][0] == route["waypoints"][-1] == "Obelisco"
    assert len(middle) == len(set(middle)), "the course must not revisit landmarks"
    assert abs(route["raw_network_distance_km"] - 42.195) < 0.25
    assert middle.index("La Boca") < middle.index("Caballito")
    assert middle.index("Caballito") < middle.index("Vicente Lopez")
    assert middle.index("Vicente Lopez") < middle.index("Recoleta")


def test_water_stations_scale_with_the_field(rt):
    small = rt.add_water_stations(participants=5000)
    big = rt.add_water_stations(participants=30000)
    assert small["water_station_count"] == big["water_station_count"]
    assert big["total_cups"] > small["total_cups"]


def test_medical_tents_are_reinforced_after_the_wall(rt):
    tents = rt.add_medical_tents(participants=30000)["tents"]
    late = [t for t in tents if t["km_mark"] >= 30]
    assert late and all(t["level"] == "advanced" for t in late)
    assert all(t["ambulance_on_site"] for t in late)
