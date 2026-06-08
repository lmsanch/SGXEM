# Platform Registry — Drone & UAV Specifications

## Rotary-Wing Platforms

| Platform | Rotor Count | Max Diameter | MTOW | Endurance | Top Speed | Acoustic Signature Class | Operator Type |
|---|---|---|---|---|---|---|---|
| DJI Matrice 300 RTK | 4 | 0.84 m | 2.7 kg | 55 min | 82 km/h | Quadcopter-medium | Commercial |
| DJI Mavic 3 Enterprise | 4 | 0.48 m | 0.96 kg | 45 min | 75 km/h | Quadcopter-small | Commercial |
| Skydio X10 | 4 | 0.60 m | 3.5 kg | 40 min | 65 km/h | Quadcopter-medium | Government |
| Autel EVO II Pro | 4 | 0.52 m | 1.2 kg | 40 min | 72 km/h | Quadcopter-small | Commercial |
| Freefly Alta X | 8 | 1.2 m | 18 kg | 30 min | 55 km/h | Octocopter-heavy | Industrial |
| Intel Falcon 8+ | 8 | 0.55 m | 3.4 kg | 26 min | 50 km/h | Octocopter-light | Government |
| DJI Agras T40 | 6 | 1.3 m | 40 kg | 20 min | 40 km/h | Hexacopter-heavy | Agricultural |
| Custom hex recon | 6 | 0.80 m | 8 kg | 35 min | 60 km/h | Hexacopter-medium | Military |

## Fixed-Wing Platforms

| Platform | Engine Type | Wingspan | MTOW | Endurance | Top Speed | Acoustic Signature Class | Operator Type |
|---|---|---|---|---|---|---|---|
| RQ-20 Puma | Electric pusher | 2.8 m | 6.8 kg | 3.5 hr | 83 km/h | Fixed-wing-electric | Military |
| RQ-11B Raven | Electric pusher | 1.4 m | 1.9 kg | 90 min | 95 km/h | Fixed-wing-electric | Military |
| ScanEagle | Gas inline | 3.1 m | 22 kg | 24 hr | 150 km/h | Fixed-wing-gas | Military |
| MQ-9 Reaper | Turboprop | 20 m | 4,760 kg | 27 hr | 480 km/h | Fixed-wing-turbine | Military |
| Penguin B | Gas inline | 3.0 m | 9.5 kg | 20 hr | 120 km/h | Fixed-wing-gas | Government |

## Key Cross-References

1. **Quadcopter** platforms have 4 rotors and produce a characteristic "buzz" at 80–200 Hz fundamental.
2. **Hexacopter** platforms have 6 rotors with lower fundamental (50–150 Hz) and higher MTOW.
3. **Octocopter** platforms have 8 rotors, lowest fundamental (30–100 Hz), highest MTOW for rotary.
4. Rotor count directly determines: MTOW class, acoustic signature class, and IR motor-pod count.
5. All DJI 4-rotor platforms share the same acoustic signature class regardless of size.
6. Military fixed-wing gas/turbine platforms are acoustically distinct from electric at ranges >500 m.
7. **Custom hex recon** is the only military hexacopter in the registry — 6 rotors, 8 kg MTOW.
