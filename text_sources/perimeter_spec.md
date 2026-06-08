# Perimeter Specification — Intrusion Detection Thresholds

## Depth-Based Obstacle Classification

| Obstacle Type | Height Range (depth) | Width Range | Material Class | Detection Confidence | Response Protocol | Notes |
|---|---|---|---|---|---|---|
| Vehicle barrier (concrete) | 0.8–1.2 m | 2.0–3.0 m | Rigid-solid | 95% | Vehicle barrier breach | Jersey barrier profile |
| Vehicle barrier (steel) | 0.6–1.0 m | 1.5–2.5 m | Rigid-metal | 92% | Vehicle barrier breach | Bollard or wedge gate |
| Person (standing) | 1.5–2.0 m | 0.4–0.8 m | Soft-organic | 85% | Perimeter intrusion | Depth silhouette; movement distinguishes from post |
| Person (crouching) | 0.8–1.2 m | 0.5–1.0 m | Soft-organic | 70% | Perimeter intrusion | Low confidence; similar height to barrier |
| Crawling intruder | 0.2–0.5 m | 0.5–1.0 m | Soft-organic | 45% | Perimeter intrusion | Very low confidence; easily confused with ground clutter |
| Vehicle (sedan) | 1.2–1.5 m | 1.6–2.0 m | Rigid-metal | 88% | Vehicle barrier breach | Standard civilian car profile |
| Vehicle (SUV/truck) | 1.5–2.2 m | 1.8–2.5 m | Rigid-metal | 90% | Vehicle barrier breach | Larger profile; higher confidence |
| Debris pile | 0.3–1.5 m | 0.5–3.0 m | Mixed | 60% | Suspicious package | Irregular profile; requires thermal fusion |
| Fence line | 1.8–2.5 m | < 0.2 m | Rigid-metal | 97% | No response (infrastructure) | Thin vertical profile; filter from alerts |
| Wall segment | 2.0–4.0 m | 0.2–0.5 m | Rigid-solid | 98% | No response (infrastructure) | Thick vertical; highest confidence as non-threat |
| Dog/animal | 0.3–1.0 m | 0.3–0.8 m | Soft-organic | 55% | No response (wildlife) | Similar to crawling intruder; thermal fusion needed |

## Depth Threshold Alert Rules

| Depth Threshold | Alert Level | Condition | Auto-Response |
|---|---|---|---|
| 0.0–0.2 m | NONE | Ground plane | Ignore |
| 0.2–0.5 m | LOW | Crawling intruder zone | Log; thermal fusion check |
| 0.5–0.8 m | MEDIUM | Low obstacle / crouching | Flag; acoustic check |
| 0.8–1.2 m | HIGH | Barrier / person-height | Alert; standoff protocol activate |
| 1.2–2.0 m | CRITICAL | Vehicle / standing person | Immediate alert; weapon-ready |
| 2.0–4.0 m | INFRASTRUCTURE | Wall / fence / building | Filter from alerts |
| > 4.0 m | ANOMALY | Unknown large object | Log for review; possible sensor error |

## Cross-Reference Rules

1. **Vehicle barrier** (both concrete and steel) falls in 0.6–1.2 m height → triggers HIGH or CRITICAL alert.
2. **Crouching person** (0.8–1.2 m) and **vehicle barrier** overlap in depth profile — thermal fusion is required to disambiguate.
3. **Fence line** and **wall** are always filtered as infrastructure — depth profile alone suffices (thin vs thick vertical).
4. **Crawling intruder** has the lowest detection confidence (45%) and requires thermal confirmation to distinguish from ground clutter.
5. **SUV/truck** profile (1.5–2.2 m) is the only vehicle type that overlaps with **standing person** height — width disambiguates.
6. All depth thresholds assume sensor height of 3 m and downward viewing angle of 15–45°.
7. Depth readings above 4.0 m are typically sensor artifacts — flag but do not alert.
8. The **15 m standoff distance** for vehicle barrier events comes from the urban threat playbook, not this document.
