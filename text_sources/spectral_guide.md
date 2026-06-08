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
