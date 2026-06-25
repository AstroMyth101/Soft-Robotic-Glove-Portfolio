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

1. Add a public-safe block diagram image.
2. Add sanitized photos of the bench setup.
3. Add a small sample CSV log with fake or redacted values.
4. Add a short demonstration video link.
5. Add a simplified firmware excerpt, not the full private firmware.
6. Add a calibration worksheet.

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

This public portfolio should eventually include:

- system overview diagram
- wiring diagram
- state diagram
- calibration guide
- validation checklist
- sample telemetry
- release notes
- short project demo video

A good engineering portfolio should show the work, not merely claim the work.
