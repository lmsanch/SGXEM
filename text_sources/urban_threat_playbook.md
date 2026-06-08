# Urban Threat Playbook — Standoff Distances & Response Protocols

## Standoff Distances by Event Type

| Event Type | Min Standoff Distance | Response Time | Threat Level | Sensor Priority | Notes |
|---|---|---|---|---|---|
| Vehicle barrier breach | 15 m | 30 sec | CRITICAL | Thermal + depth | Vehicle class determines response force size |
| Active shooter (small arms) | 50 m | 60 sec | CRITICAL | Acoustic + thermal | Gunshot classification drives weapon-type response |
| IED detonation | 100 m | 2 min | CRITICAL | Thermal + depth | Secondary device standoff is 200 m |
| UAV incursion | 75 m | 45 sec | HIGH | Acoustic + thermal | Rotor count determines intercept asset |
| Suspicious package | 25 m | 90 sec | HIGH | Depth + thermal | X-ray equivalent via depth profiling if available |
| Perimeter intrusion (person) | 10 m | 20 sec | MEDIUM | Depth + thermal | Fence-line sensor fusion required |
| Crowd agitation | 30 m | 3 min | LOW | Acoustic | Voice-level monitoring for escalation cues |
| Vehicle barrier (stationary) | 15 m | 5 min | MEDIUM | Depth | Obstacle classification from depth map |

## Response Protocols by Threat Level

### CRITICAL
1. Immediate alert to command post
2. Weapon-free posture within standoff radius
3. Sensor fusion override — all modalities active
4. 30-second situational update cycle

### HIGH
1. Alert to watch officer
2. Weapon-ready posture within standoff radius
3. Primary sensor + one backup active
4. 60-second situational update cycle

### MEDIUM
1. Log to incident tracker
2. Weapon-safe posture
3. Primary sensor only
4. 5-minute situational update cycle

### LOW
1. Log to daily summary
2. Standard patrol posture
3. Routine sensor schedule
4. 15-minute situational update cycle

## Cross-Reference Rules

1. **Vehicle barrier breach** and **stationary vehicle barrier** share the same standoff distance (15 m) but differ in response time (30 sec vs 5 min) based on motion state.
2. **UAV incursion** standoff (75 m) is determined by rotor count: 4-rotor = 50 m, 6-rotor = 75 m, 8-rotor = 100 m. The table shows the average.
3. **Active shooter** standoff depends on acoustic classification: handgun = 50 m, rifle = 75 m, automatic = 100 m.
4. **IED detonation** has the largest standoff (100 m) due to secondary device risk.
5. All standoff distances assume open terrain; reduce by 50% in urban canyons.
6. **Perimeter intrusion** has the shortest standoff (10 m) and fastest response (20 sec) — fence-line proximity makes delayed response untenable.
