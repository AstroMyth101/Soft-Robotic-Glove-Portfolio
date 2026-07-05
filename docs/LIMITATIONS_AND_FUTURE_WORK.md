# Limitations and Future Work

## Current limitations

| Limitation | Practical meaning |
|---|---|
| Shared pneumatic source | Fingers cannot receive independent pressure levels with the current hardware |
| Flex sensors only | Finger angle can be estimated, but force is not measured |
| Minimal branch has no large fault framework | STOP and bench power control are important during tests |
| No pressure/vacuum sensors in the minimal branch | Pneumatic state is inferred from command and motion, not directly measured |
| Manual calibration required | Flex sensor mapping depends on mounting, divider values, board ADC behavior, and glove geometry |
| Bench-only documentation | This portfolio is not a product release |

---

## Short-term improvements

Delivered in this repository:

- ~~System and pneumatic block diagrams~~ — Mermaid diagrams in [`ARCHITECTURE.md`](ARCHITECTURE.md)
- ~~State diagram~~ — FSM diagram in [`ESP32S3_CONTROLLER_OVERVIEW.md`](ESP32S3_CONTROLLER_OVERVIEW.md)
- ~~Sample CSV logs with dummy values~~ — both schemas under [`../samples/`](../samples/)
- ~~Simplified firmware excerpts~~ — two excerpts under [`../firmware_snippets/`](../firmware_snippets/)
- ~~Calibration worksheet~~ — [`CALIBRATION_WORKSHEET.md`](CALIBRATION_WORKSHEET.md)
- ~~Validation summary~~ — [`BENCH_VALIDATION_SUMMARY.md`](BENCH_VALIDATION_SUMMARY.md)
- ~~Runnable telemetry tooling~~ — [`../tools/`](../tools/)

Still open:

1. Add sanitized photos of the bench setup.
2. Add a short demonstration video link.

---

## Technical upgrades

Future engineering branches may add:

- pressure sensor feedback
- vacuum sensor feedback
- better flex-sensor calibration
- IMU telemetry
- EMG input for intention estimation
- SD logging
- Wi-Fi dashboard
- ROS 2 or micro-ROS bridge
- external ADC for cleaner sensor expansion
- current monitoring
- stronger hardware safety layer

---

## Control upgrades

Possible control improvements:

- PI control with anti-windup
- per-finger completion logic using individual targets
- valve dwell timing to reduce chatter
- pneumatic pressure limits based on sensor feedback
- repeatability analysis from logs
- automated calibration routines

The rule stays the same: control logic must respect the real pneumatic hardware.

---

## Documentation upgrades

Now included: system overview and pneumatic diagrams, a state diagram, a
calibration worksheet, a validation checklist and summary, sample telemetry in
both CSV schemas, and runnable analysis tooling.

Still to come:

- a drawn wiring diagram (the wiring is currently documented as tables)
- release notes for future public milestones
- a short project demo video

A good engineering portfolio should show the work, not merely claim the work.
