# Marathon Planning Guide

> NOT IN THE CODELAB. The `route-planning` SKILL.md references this file, but no
> codelab step creates it. Written for this repo so the Skill resolves.

## 1. Certified distance

- Marathon: **42.195 km / 26.2 miles**. World Athletics tolerance is +0.1% and
  never short, so courses are measured at 42.237 km and trimmed on site.
- Measurement uses the **shortest possible route** a runner could take (SPR),
  measured with a calibrated bicycle (Jones counter), 1 m from each curb.
- Half marathon 21.0975 km, 10K 10 km, 5K 5 km.

## 2. Road types and closure severity

| Road type  | Surface | Min. width | Closure severity | Typical detour cost |
|------------|---------|-----------:|-----------------:|---------------------|
| Boulevard  | asphalt |     20 m   | 5 (highest)      | Full arterial detour, transit reroute |
| Arterial   | asphalt |     14 m   | 4                | Signed detour, 2-3 side streets |
| Street     | asphalt |      8 m   | 3                | Local access only |
| Trail      | mixed   |      4 m   | 1 (lowest)       | No vehicle impact |

Rule of thumb: **1.5 m of course width per 1,000 runners** at the start, tapering
to 1.0 m after 5 km once the field spreads.

## 3. Start and finish

- Start corral capacity: **2 runners per m²** of corral area.
- Waves every 3-5 minutes, max 3,000 runners per wave.
- Finish chute: minimum 100 m long, 10 m wide, then a 2,000 m² recovery area.
- Baggage: 1 truck per 1,500 runners, retrieved within 15 minutes.

## 4. On-course services

- **Water**: every 2.5 km (metric) or every 2 miles; 2 cups per runner per station.
- **Sports drink**: alternating stations from 7.5 km onwards.
- **Medical**: every 5 km, plus reinforced tents after 30 km ("the wall") and at
  the finish. 1 ambulance per advanced tent, 2 in reserve.
- **Toilets**: 1 per 75 runners at the start, 1 per 200 on course.
- **Marshals**: 1 per intersection, 1 per 100 m on technical sections.

## 5. Emergency access (drives the `safety_compliance` score)

- Never fully enclose a hospital, fire station or police station. Every such
  facility needs a documented detour and a crossing point.
- Emergency vehicle crossing points every **3.2 km (2 miles)**, staffed.
- At least one evacuation corridor per 5 km of course, kept clear.
- Course sweep vehicle behind the final runner; cut-off pace typically 6:30/km.

## 6. Community impact (drives the `community_impact` score)

- Notify residents and businesses along the course **30 days** in advance.
- Amplified sound no earlier than 06:00 local; cheer zones away from hospitals
  and care homes.
- Distribute the course across neighbourhoods rather than concentrating the
  disruption in one district.
- Reopen roads progressively behind the sweep vehicle, not all at the end.

## 7. Budget reference (30,000-runner city marathon, USD)

| Line item                  | Cost      |
|----------------------------|----------:|
| Permits and police         |  450,000  |
| Timing and results         |  180,000  |
| Medical and safety         |  260,000  |
| Course infra and barriers  |  520,000  |
| Water, nutrition, toilets  |  310,000  |
| Medals, shirts, expo       |  640,000  |
| Marketing and staff        |  380,000  |
| **Total**                  | **2,740,000** |

Revenue: registration (60-70%), sponsorship (20-30%), expo and merchandise
(5-10%), charity partnerships. A plan that relies on registrations alone scores
poorly on `financial_viability`.
