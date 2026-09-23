---
name: route-planning
description:
  Generates high-fidelity marathon routes using ordered scenic loops and Dijkstra
  and outputting GeoJSON for visualization.
---

# Route Planning Skill

**Goal:** Design a mathematically perfect 42.195 km marathon route using real road network data.

## Capabilities

- **Automated Route Generation**: Uses a built-in road network. Curated showcase cities can define a single-direction scenic loop; the generic planner uses Dijkstra between landmarks.
- **GeoJSON Output**: Returns a standards-compliant GeoJSON FeatureCollection.

## Resources

### Tools (Python)
- `tools.py`: Contains the `plan_marathon_route`, `add_water_stations`, and `add_medical_tents` implementations.

### References
- `references/marathon_planning_guide.md`: Marathon standards, road width, traffic severity, landmarks.
