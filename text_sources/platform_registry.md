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

## Vessel Classes — Underwater Acoustic Signatures

| Vessel Class | Propeller Blades | Typical Speed | Shaft Rate at 12 kts | Acoustic Signature Band | DEMON Fundamental | Notes |
|---|---|---|---|---|---|---|
| Container ship (Panamax) | 5 | 14–20 kts | 1.8–2.3 Hz | 50–400 Hz; 5× blade-rate harmonics | 9–11 Hz at 12 kts | Largest commercial vessel class; low shaft rate |
| Tanker (VLCC) | 4 | 12–16 kts | 1.4–2.0 Hz | 30–300 Hz; 4× blade-rate harmonics | 5.6–8.0 Hz at 12 kts | Heaviest laden displacement; lowest shaft rate of any commercial class |
| Passenger ferry | 6 | 18–28 kts | 3.0–4.5 Hz | 80–600 Hz; 6× blade-rate harmonics | 18–27 Hz at 20 kts | High speed; highest blade-rate of commercial classes; distinctive 6× spacing |
| Tug | 4 | 8–14 kts | 2.5–4.0 Hz | 60–500 Hz; variable | 10–16 Hz | Short hull, high propeller cavitation; often present near harbor approaches |
| Fishing trawler | 3–4 | 10–14 kts | 2.0–3.5 Hz | 40–400 Hz; winch gear harmonics | 6–14 Hz | Winch/trawl gear adds harmonics at 20–80 Hz; distinguishable from tanker by gear noise |

## Submarine Classes

| Class | Type | Propulsion | Propeller Blades | Snorkel Noise Band | Electric-Only Band | Key Discriminant |
|---|---|---|---|---|---|---|
| Project 636 Varshavyanka (Kilo-class) | Diesel-electric SSK | Diesel + lead-acid battery | 7 | 50–200 Hz (strong diesel harmonics) | 40–120 Hz (faint motor tonals) | Snorkel phase is loudest; 7-blade prop at ~2.5 Hz shaft rate |
| Type 212A (AIP) | Fuel cell AIP SSK | Siemens PEM fuel cell + Li-ion | 7 | N/A (no snorkel required) | 20–80 Hz (near-silent) | Near-undetectable on AIP; no diesel tonal; occasional pump transient |
| Virginia-class (SSN) | Nuclear attack | S9G reactor | 7 | N/A | Reactor: 80–300 Hz (coolant pump) | Reactor coolant pump is primary tonal; turbine at 2–8 kHz; detectable at > 50 km with LOFAR |
| Gotland-class | AIP SSK | Stirling engine AIP | 5 | N/A | 30–120 Hz (Stirling harmonics at 1–3 Hz) | Stirling engine creates low-frequency harmonic series even on AIP — discriminant vs. Type 212 |

## Key Cross-References (Vessel + Submarine)

1. **7-blade submarines** (Kilo, Type 212, Virginia) produce 7× shaft-rate in DEMON spectrum; vessels rarely exceed 6 blades.
2. **Virginia-class reactor coolant pump** (80–300 Hz) is the primary acoustic discriminant — no commercial vessel has a continuous tonal in this band.
3. **Kilo-class snorkeling** produces the strongest signature (50–200 Hz diesel + 7× shaft harmonics); electric-only mode is nearly silent — the same classification challenge as whale vs. submarine.
4. **Tanker VLCC** (4-blade, lowest shaft rate) is most likely to be confused with a quiet SSK at long range — DEMON blade count (4 vs 7) is the primary disambiguator.
5. **Passenger ferry** (6-blade, highest commercial shaft rate) is most likely to be confused with Gotland-class Stirling harmonics — temporal pattern (continuous vs. harbor-approach) disambiguates.
