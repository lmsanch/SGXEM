# Anti-Submarine Warfare (ASW) Playbook — Standoff Distances & Response Protocols

## Submarine Contact Protocols by Vessel Class

| Contact Class | Torpedo Loadout | Torpedo Range | Propulsion | Acoustic Signature Band | Response Protocol | Recommended Standoff |
|---|---|---|---|---|---|---|
| Diesel-electric attack submarine (Project 636 Kilo-class) | 6× 533mm tubes, TEST-71 active/passive homing, SET-65 wake-homing | 15 km (active), 20 km (passive) | Diesel-electric, 17 kts submerged | 50–200 Hz (snorkeling), near-silent electric-only | INCREASE DEPTH to layer, reduce speed to 3 kts, alter course 045° to open range | ≥ 20 km |
| Nuclear attack submarine (Virginia-class SSN) | 12× VLS + 4× 533mm, Mk-48 ADCAP, Tomahawk | 50+ km | Nuclear, 34 kts submerged | Reactor coolant pump: 80–300 Hz; turbine: 2–8 kHz | Maximum sprint to layer, deploy MOSS decoy, active pinging restricted | ≥ 30 km |
| Air-independent propulsion submarine (Type 212 AIP) | 6× 533mm, DM2A4 Seahake | 14 km | Fuel cell AIP, 8 kts on AIP | Near-silent < 100 Hz; occasional pump transient 200–400 Hz | Passive track only; no active sonar — AIP signature too low to hold in reverberation | ≥ 25 km |
| UUV / underwater drone contact | Depends on payload; typically acoustic tag or limpet | Proximity activation | Battery electric, 6–12 kts | 400–1200 Hz propeller whine; no engine tonals | Intercept geometry; call for surface or air ASW asset | ≥ 5 km |
| Surface contact — escort frigate | Mk-46 / Mk-54 torpedo, ASROC, ship-launched depth charge | 11 km (ASROC) | Gas turbine + diesel, 28 kts | 50–400 Hz hull vibration; propeller cavitation 500 Hz+ | Depth change + course change; correlate with ESM intercept | ≥ 15 km |
| Biological false positive — blue whale | None | N/A | Muscle-driven flukes | B-call: 15–100 Hz tonal; A-call: amplitude-modulated 16–28 Hz | Reclassify as biologic; log call type, bearing, SNR; maintain passive track | N/A |
| Biological false positive — fin whale | None | N/A | Muscle-driven flukes | 20-Hz pulse train, 18–28 Hz, regular cadence | Reclassify as biologic; intercall interval 20–30 sec is diagnostic | N/A |
| Unknown contact | Unknown | Unknown | Unknown | Broadband or unresolved | Passive track only; DO NOT classify; escalate to sonar supervisor | ≥ 30 km (precautionary) |

## Response Protocols by Threat Level

### CRITICAL (attack submarine, surface escort)
1. Report contact to command: bearing, frequency, estimated range, confidence
2. Execute beam-to-stern geometry — reduce aspect to minimize own-ship noise
3. Reduce speed to < 5 kts; secure all non-essential rotating machinery
4. Prepare MOSS decoy for launch on command
5. Active sonar hold — do not transmit; passive only until ordered
6. 30-second contact update cycle

### HIGH (UUV contact, unclassified submarine)
1. Report contact; initiate track correlation across array elements
2. Altitude/depth change maneuver to exploit thermocline gradient
3. Request aerial ASW support (P-8, helicopter with dipping sonar)
4. Do not close range; hold current course + speed until classification improves
5. 60-second contact update cycle

### MONITOR (AIP submarine, unknown contact)
1. Assign passive track number; log all frequency/bearing data
2. No maneuver change; minimize own-ship noise
3. Coordinate with tactical officer for correlation with environmental data
4. 5-minute contact update cycle

### BIOLOGIC (whale song, fish schooling, shrimp noise)
1. Log contact as biologic with species confidence and call type
2. Retain in track log for environmental baseline analysis
3. Use as ambient noise calibration reference for sonar system
4. No tactical action

## Cross-Reference Rules

1. **Project 636 Kilo-class** is the most common diesel-electric in service globally; 20 km standoff applies under typical sea state 3 conditions.
2. **Virginia-class** reactor tonals at 80–300 Hz are present in all operating modes; fuel cell AIP (Type 212) has no equivalent signature.
3. **Blue whale B-calls** occupy 15–100 Hz — the same band as Kilo-class machinery tonals during snorkeling. Disambiguation requires SNR > 15 dB and spectral shape analysis.
4. **Fin whale 20-Hz pulses** are the most common biologic false positive in Atlantic ASW operations — regular intercall interval (20–30 sec) is the key discriminator.
5. AIP submarines (Type 212, Gotland) have the lowest acoustic signature of any operational class; passive track often requires > 4 array elements for bearing resolution.
6. All standoff distances assume open ocean; increase 30% in littoral environments due to multipath and reverberation.
7. **Unknown contact**: always treat as CRITICAL until classified — default to max standoff.
