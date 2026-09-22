from src.planner_agent.visualization.race_map import _position_on_route, build_animated_race_map


def _route():
    return {
        "start_finish": "Obelisco",
        "total_distance_km": 42.195,
        "waypoints": ["Obelisco", "Puerto Madero", "Obelisco"],
        "route_geojson": {
            "features": [{
                "geometry": {
                    "coordinates": [
                        [-58.3816, -34.6037],
                        [-58.3630, -34.6110],
                        [-58.3816, -34.6037],
                    ]
                }
            }]
        },
    }


def test_position_on_route_interpolates_and_clamps():
    route = [[0.0, 0.0], [10.0, 10.0]]
    assert _position_on_route(route, 0.25) == [2.5, 2.5]
    assert _position_on_route(route, -1) == [0.0, 0.0]
    assert _position_on_route(route, 2) == [10.0, 10.0]


def test_animated_map_contains_route_controls_and_markers():
    race_map = build_animated_race_map(
        _route(),
        {"stations": [{"station_id": "WS-01", "km_mark": 2.5}]},
        {"tents": [{"tent_id": "MED-01", "km_mark": 5}]},
        participants=30_000,
        runner_count=40,
    )
    html = race_map.get_root().render()
    assert "Buenos Aires 42K" in html
    assert "runnerCount = 40" in html
    assert "30000" in html
    assert "WS-01" in html
    assert "MED-01" in html
    assert "42.195 km" in html
