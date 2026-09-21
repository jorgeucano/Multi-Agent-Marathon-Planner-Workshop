---
name: route-planning
description:
  Generates high-fidelity marathon routes using road network data (Dijkstra's algorithm)
  and outputting GeoJSON for visualization.
---

# Route Planning Skill

**Goal:** Design a mathematically perfect 42.195 km marathon route using real road network data.

## Capabilities

- **Automated Route Generation**: Uses a built-in road network and Dijkstra's algorithm to calculate a certified 42.195 km route between specified landmarks.
- **GeoJSON Output**: Returns a standards-compliant GeoJSON FeatureCollection.

## Resources

### Tools (Python)
- `tools.py`: Contains the `plan_marathon_route`, `add_water_stations`, and `add_medical_tents` implementations.

### References
- `references/marathon_planning_guide.md`: Marathon standards, road width, traffic severity, landmarks.
