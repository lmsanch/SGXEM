# Spectral Guide — Frequency Bands & Acoustic Signatures

## Acoustic Source Types and Frequency Bands

| Source Type | Frequency Band | Peak Frequency | Harmonics | Detection Range (open) | ID Confidence | Notes |
|---|---|---|---|---|---|---|
| Gunshot (handgun) | 500–4000 Hz | 1200 Hz | 2nd at 2400 Hz | 800 m | 92% | Impulsive; muzzle blast + shock wave |
| Gunshot (rifle) | 200–3000 Hz | 800 Hz | 2nd at 1600 Hz | 1200 m | 89% | Longer barrel = lower fundamental, wider shock |
| Gunshot (automatic) | 200–4000 Hz | 900 Hz | Multi-burst pattern | 1500 m | 95% | Burst cadence is diagnostic; 3–5 round groups |
| Helicopter rotor | 20–500 Hz | 80 Hz (blade pass) | 2x, 4x, 6x BPF | 3000 m | 97% | Blade-pass frequency = N_blades × RPM/60 |
| Fixed-wing propeller | 40–800 Hz | 120 Hz | 2x, 3x | 2500 m | 85% | Prop RPM determines fundamental |
| UAV rotor (quadcopter) | 80–2000 Hz | 150 Hz | 2nd at 300 Hz | 400 m | 78% | High RPM, small blades; easily masked by wind |
| UAV rotor (hexacopter) | 50–1500 Hz | 100 Hz | 2nd at 200 Hz | 600 m | 82% | Lower RPM, larger blades than quad |
| Diesel engine (heavy) | 30–500 Hz | 80 Hz | 2x, 3x, 4x firing | 1200 m | 90% | Firing frequency = (RPM × cylinders)/(2 × 60) for 4-stroke |
| Gasoline engine (light) | 100–2000 Hz | 300 Hz | 2x, 4x firing | 500 m | 75% | Higher fundamental; less distinctive |
| Turbine (aircraft) | 2000–8000 Hz | 4000 Hz | N1, N2 shafts | 5000 m | 94% | High-frequency whine; longest detection range |
| Siren (emergency) | 500–3000 Hz | 800 Hz | Sweep 500–1800 Hz | 1000 m | 98% | Frequency sweep is unique identifier |
| Dog bark | 300–2500 Hz | 700 Hz | Variable | 200 m | 60% | Low confidence; high inter-class variance |
| Human voice (shouting) | 200–4000 Hz | 500 Hz | Vocal formants | 150 m | 55% | Lowest confidence; high variability |
| Explosive detonation | 10–10000 Hz | 100 Hz (broadband) | None | 2000 m | 88% | Broadband impulsive; distinct from gunshot by duration |

## Spectral Classification Decision Tree

```
Impulsive?
├── YES → Duration < 100ms?
│         ├── YES → Repetition rate > 5 Hz?
│         │         ├── YES → Automatic weapon fire
│         │         └── NO → Peak > 2 kHz?
│         │                 ├── YES → Handgun
│         │                 └── NO → Rifle
│         └── NO (> 100ms) → Broadband?
│                   ├── YES → Explosive detonation
│                   └── NO → Vehicle backfire
└── NO (sustained) → Fundamental < 200 Hz?
          ├── YES → Rotor beat?
          │         ├── YES → BPF count → helicopter / multi-rotor
          │         └── NO → Diesel engine
          └── NO (> 200 Hz) → Sweep pattern?
                    ├── YES → Siren
                    └── NO → Fundamental > 2 kHz?
                              ├── YES → Turbine
                              └── NO → Gasoline engine / UAV rotor / voice
```

## Cross-Reference Rules

1. **Helicopter rotor** is uniquely identified by blade-pass frequency harmonics (2x, 4x, 6x BPF).
2. **Automatic weapon fire** is uniquely identified by burst cadence (3–5 round groups at 8–12 Hz).
3. **UAV rotors** overlap with gasoline engines at 100–2000 Hz; rotor count disambiguates quad vs hex.
4. **Turbine** has the highest detection range (5 km) and highest confidence (94%) due to unique high-frequency signature.
5. **Human voice** and **dog bark** have the lowest confidence and shortest range — never use as primary classification.
6. **Siren** is the only source with a frequency sweep — structurally unique, no confusion possible.
7. **Explosive detonation** is broadband impulsive with duration >100 ms, distinguishing it from gunshot (<100 ms).

## Underwater Acoustic Sources — Extended Frequency Reference

| Source Type | Frequency Band | Peak Frequency | Detection Range (open ocean) | Classification Method | Notes |
|---|---|---|---|---|---|
| Blue whale B-call | 15–100 Hz | 16 Hz (fundamental) | 500+ km (deep sound channel) | LOFAR tonal + amplitude envelope | Duration 30–180 sec; upcall sweep from 16 → 28 Hz; strongest biologic signal in ocean |
| Fin whale 20-Hz pulse | 18–28 Hz | 20 Hz | 300+ km | LOFAR pulse train; intercall interval 20–30 sec | Most common North Atlantic biologic false positive for passive sonar; regular cadence is diagnostic |
| Humpback whale song | 100–4,000 Hz | 300–500 Hz | 50 km | Spectrogram pattern matching; phrase+theme structure | Complex hierarchical structure; seasonal; males only |
| North Atlantic right whale upcall | 100–300 Hz | 150 Hz | 30 km | LOFAR + frequency sweep 70 → 150 Hz | Critically endangered; 5 sec duration; broadband sweep signature |
| Sperm whale click train | 500–25,000 Hz | 3,000 Hz | 5–15 km | Inter-click interval (ICI) 0.5–2 sec | Echolocation clicks; loudest biological transient; used for depth estimation via ICI pattern |
| Kilo-class diesel (snorkeling) | 50–200 Hz | 80 Hz | 20 km (LOFAR array) | LOFAR harmonics + DEMON 7× shaft-rate | Diesel firing frequency at 3–8 Hz; 7-blade propeller gives DEMON peak at 7× shaft rate |
| Virginia-class reactor coolant pump | 80–300 Hz | 120 Hz | 50+ km (convergence zone) | LOFAR CW tonal; no amplitude modulation | Continuous tonal at reactor pump frequency; unique — no biological or commercial source is equivalent |
| Type 212 AIP submarine (on fuel cell) | 20–80 Hz | 30 Hz | < 5 km (near-silent) | Occasional pump transient at 200–400 Hz; no sustained tonal | Near-threshold detection even with LOFAR; closest analog to blue whale infrasound at 20–80 Hz |
| Container ship propeller | 50–400 Hz | 120 Hz (5× shaft-rate) | 30 km | DEMON 5-blade pattern; broadband cavitation above 500 Hz | Cavitation onset above 16 kts; broadband noise floor increases 6 dB per octave above 500 Hz |
| Snapping shrimp (colony) | 2,000–200,000 Hz | 5,000 Hz | < 1 km | Broadband impulsive; no tonal structure | Pervasive tropical and subtropical background; effectively noise floor above 2 kHz in warm water |
| Ambient ocean noise (Beaufort 3) | 10–100,000 Hz | 500 Hz | Background | Frequency-dependent level: −40 dBPa²/Hz at 100 Hz | Wind-generated whitecap noise dominates 100 Hz–10 kHz; shipping noise dominates 10–100 Hz |

## Underwater Classification Decision Tree

## Underwater Classification Decision Tree

```
Tonal (continuous-wave) signal present?
├── YES → Continuous (not pulsed)?
│         ├── YES → Frequency band 80–300 Hz?
│         │         ├── YES → No biological equivalent → Nuclear submarine reactor pump
│         │         └── NO (< 80 Hz) → AIP submarine, blue whale B-call, fin whale pulse
│         └── NO (pulsed) → Intercall interval 20–30 sec?
│                   ├── YES → Fin whale 20-Hz pulse (biologic)
│                   └── NO  → Blue whale B-call sweep (16–28 Hz) or unknown biologic
└── NO (broadband) → Impulsive?
          ├── YES → Duration < 1 ms → Snapping shrimp (colony) or sperm whale click
          └── NO (sustained broadband) → DEMON analysis: blade count?
                    ├── 7-blade DEMON peak → Submarine (Kilo/Virginia/Type 212)
                    ├── 4–6-blade DEMON peak → Commercial vessel
                    └── No DEMON structure → Ambient weather noise or distant shipping
```




## LOFAR vs DEMON Analysis Summary

| Technique | Domain | What It Detects | Resolution | Use Case |
|---|---|---|---|---|
| LOFAR | Frequency (< 1 kHz) | Continuous-wave tonals from rotating machinery | 0.03–0.1 Hz | Machinery line spectrum; reactor pump; propeller fundamental |
| DEMON | AM envelope of broadband | Propeller shaft rate and blade count | 0.01–0.1 Hz | Vessel classification; blade count = shaft rate × blades |
| LOFAR + DEMON combined | Both | Full signature including tonals AND blade count | High | Gold standard for passive contact classification |

## Cross-Reference Rules (Underwater Layer)

1. **Fin whale 20-Hz pulses** and **Kilo-class diesel tonals** both occupy 50–200 Hz; intercall interval (20–30 sec biologic vs. continuous mechanical) is the primary discriminant.
2. **DEMON analysis** yields blade count — 7-blade submarine vs. 4–6-blade vessel is a key classifier.
3. **Blue whale B-call** (15–100 Hz) is the lowest-frequency biologic — any tonal below 15 Hz in the ocean is almost certainly mechanical.
4. **Virginia-class reactor pump** is the only source producing a continuous CW tonal in the 80–300 Hz band in open ocean — no commercial vessel or biologic equivalent.
5. **Snapping shrimp** create a noise floor above 2 kHz in tropical/subtropical waters — any signal above this floor is effectively buried in shrimp noise at < 1 km.
