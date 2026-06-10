# Hydrophone & Passive Acoustic Sensor Specifications

## Passive Acoustic Sensor Types and Frequency Coverage

| Sensor Type | Frequency Range | Sensitivity | Max Detection Range | Deployment | Notes |
|---|---|---|---|---|---|
| DIFAR sonobuoy (AN/SSQ-53F) | 10–2,400 Hz | −160 dBV/µPa | 5 km (calm sea) | Air-dropped, expendable, 1–8 hr life | Directional + omni channels; bearing ambiguity resolved by DIFAR processing |
| LOFAR (Low-Frequency Analysis and Recording) array | 10–1,000 Hz | −175 dBV/µPa | 80 km (convergence zone) | Bottom-mounted or towed | Designed for narrowband tonal detection (machinery line spectra); DEMON analysis on AM carrier |
| MEMS underwater microphone (research grade) | 20 Hz–10 kHz | −145 dBV/µPa | 5 m (direct path) | ROV-mounted or diver-deployed | Short range; useful for close-in contact classification and bioacoustic tagging |
| Bottom-mounted hydrophone (SanctSound equivalent) | 10–200 Hz | −180 dBV/µPa | 50 km | Permanently moored on seafloor | Low-frequency optimized; used for whale census and ambient noise baseline; co-deployed by NOAA and U.S. Navy under SanctSound program |
| Broadband towed hydrophone array | 20–10,000 Hz | −160 dBV/µPa | 20 km (passive) | Towed by ship or submarine | Full-spectrum coverage; higher noise floor due to tow cable; used for surface and submarine tracking |
| Dipping sonar (AN/AQS-22) | 500–3,000 Hz | −155 dBV/µPa | 3 km (active mode) | Helicopter-deployed, cable-suspended | Active + passive modes; helicopter hovers to deploy; primary ASW sensor for maritime patrol helos |
| Distributed acoustic sensor (DAS) — fiber optic | 1–10,000 Hz | Variable | 100 km (fiber length) | Seafloor fiber cable | Uses Rayleigh backscattering; detects whale songs, submarine machinery, seismic events on same infrastructure |
| Ambient noise monitoring buoy | 10–5,000 Hz | −165 dBV/µPa | 30 km (passive) | Surface-drifting, solar-powered | Broadband; used for ocean noise baseline, ship-traffic density, and cetacean presence |

## LOFAR and DEMON Analysis Techniques

### LOFAR (Low-Frequency Analysis and Recording)
- **Purpose**: Detect narrowband continuous-wave (CW) tonals from rotating machinery (propellers, pumps, turbines)
- **Window**: Long FFT window (4–30 sec) to achieve frequency resolution < 0.1 Hz at low frequencies
- **Frequency resolution**: 0.03–0.1 Hz typical for machinery-line-spectrum analysis
- **Key targets**: Propeller blade-rate, shaft frequency, pump harmonics, reactor coolant pump noise
- **Cetacean application**: Fin whale 20-Hz pulses, blue whale A-call at 16 Hz, humpback fundamental at 100–400 Hz

### DEMON (Demodulation of Envelope Modulation on Noise)
- **Purpose**: Detect shaft rotation rate and blade count from broadband noise AM modulation
- **Carrier frequency**: 500–5,000 Hz (broadband noise above propeller near-field)
- **Modulation frequency**: 0–500 Hz (propeller shaft harmonics)
- **Output**: Shaft frequency spectrum → propeller blade count = peak Hz / shaft RPM / 60
- **Cetacean equivalent**: Breathing rhythm modulation in dolphin echolocation trains

## Frequency Band Reference Table

| Frequency Band | Designation | Key Sources in Band | Notes |
|---|---|---|---|
| 10–100 Hz | Infrasound / Very Low Frequency | Blue whale A/B calls, fin whale 20-Hz, submarine machinery fundamentals, ship hull vibration | Requires large-aperture arrays for direction-finding; propagates > 1,000 km in deep ocean |
| 100–500 Hz | Low Frequency | Humpback song, right whale upcall, diesel engine firing, propeller blade-rate, snorkeling submarine | Primary band for diesel-electric submarine passive detection |
| 500–2,000 Hz | Mid Frequency | DIFAR tactical range, dipping sonar active, fish vocalizations, sperm whale creak | Mixed biologic + mechanical; complex classification environment |
| 2,000–10,000 Hz | High Frequency | Dipping sonar active, MEMS near-field, snapping shrimp, dolphin click trains | Attenuated rapidly with range; reliable < 5 km |
| 10,000–200,000 Hz | Ultrasonic | Dolphin / porpoise echolocation, fish ultrasound organs, bubble acoustics | Beyond most tactical sonars; biological research / UUV proximity sensing |

## Cross-Reference Rules

1. **DIFAR sonobuoy** (AN/SSQ-53F) has a 5 km detection radius — longest range of air-delivered sensors.
2. **LOFAR arrays** have the highest sensitivity (−175 dBV/µPa) and longest range (80 km to convergence zone) but require fixed bottom deployment.
3. **Bottom-mounted arrays** (SanctSound type) detect at 50 km range in the 10–200 Hz band — the same geometry as tactical passive sonar for submarine detection.
4. **MEMS sensors** have the shortest range (5 m) but highest frequency resolution — used for close-in bioacoustic tagging and ROV-based inspection.
5. **Blue whale B-calls** (15–100 Hz) and **Kilo-class machinery tonals** (50–200 Hz snorkeling) overlap in frequency — classification requires spectral shape + temporal pattern, not frequency alone.
6. **DEMON analysis** extracts shaft rate from broadband noise: dividing DEMON peak frequency by blade count gives propeller RPM — a vessel-class discriminant.
7. All sensitivity values expressed as dBV/µPa at 1 kHz unless otherwise noted; actual sensitivity varies ±10 dB across frequency band.
