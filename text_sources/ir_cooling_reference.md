# IR Cooling Reference — Thermal Persistence Times

## Platform IR Signatures After Engine Shutdown

Platform thermal persistence is the time a vehicle remains detectable by FLIR after engine shutdown. Values measured at 20°C ambient, clear sky, no wind.

### Ground Vehicles

| Platform Type | Engine Shutdown IR Persistence | Peak IR Delta (above ambient) | Cooling Half-Life | Notes |
|---|---|---|---|---|
| Wheeled APC | 45 min | +38°C | 12 min | Engine block is primary source; exhaust manifold cools first |
| Tracked IFV | 60 min | +42°C | 18 min | Track links retain heat longest; turret ring is secondary source |
| Light tactical vehicle | 20 min | +22°C | 6 min | Small block cools rapidly; no secondary thermal mass |
| Heavy transport truck | 35 min | +30°C | 10 min | Cargo bed adds thermal mass; exhaust stack is last to cool |
| MRAP | 40 min | +34°C | 11 min | V-hull shape traps engine bay heat; underbelly cools slowest |
| Motorcycle recon unit | 10 min | +15°C | 3 min | Minimal thermal mass; exhaust pipe is only detectable source after 5 min |

### Aerial Platforms

| Platform Type | Engine Shutdown IR Persistence | Peak IR Delta | Cooling Half-Life | Notes |
|---|---|---|---|---|
| Quadcopter drone (small, <5 kg) | 3 min | +8°C | 45 sec | Motor windings only; battery is not IR-visible |
| Quadcopter drone (medium, 5–25 kg) | 8 min | +14°C | 2 min | Larger motors retain more heat; visible at 1.5 km |
| Hexacopter drone (25–50 kg) | 12 min | +18°C | 3.5 min | Six motor pods; cumulative IR signature |
| Fixed-wing UAV (tactical) | 25 min | +25°C | 7 min | Engine exhaust + wing surface heating |
| Helicopter (utility) | 40 min | +35°C | 12 min | Turbine exhaust + rotor hub friction heat |
| Helicopter (attack) | 55 min | +40°C | 16 min | Heavier powertrain; engine bay insulation retains heat |

### Naval Platforms

| Platform Type | Engine Shutdown IR Persistence | Peak IR Delta | Cooling Half-Life | Notes |
|---|---|---|---|---|
| Patrol boat (fast) | 15 min | +20°C | 4 min | Water contact accelerates hull cooling; stack is last source |
| Landing craft | 30 min | +28°C | 9 min | Large engine compartment; deck retains heat above waterline |

## Cross-Reference Rules

1. **Tracked IFV** has the longest ground-vehicle persistence (60 min) due to track heat retention.
2. **Attack helicopter** has the longest overall aerial persistence (55 min).
3. Cooling half-life is the time for IR delta to drop to 50% of peak; detection range drops proportionally.
4. Below +5°C delta, most FLIR systems cannot distinguish platform from terrain clutter at ranges >1 km.
5. Water contact (naval/amphibious) generally halves persistence compared to same engine on land.
