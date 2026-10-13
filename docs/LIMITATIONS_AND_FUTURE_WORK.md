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

## Portfolio materials

The repository includes architecture and state diagrams, firmware excerpts, dummy CSV samples, calibration and validation documents, and Python analysis tools. Bench photographs and a demonstration video have not been published.

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

Any changes must account for the shared pressure/vacuum manifold.

---

## Documentation upgrades

Now included: system overview and pneumatic diagrams, a state diagram, a
calibration worksheet, a validation checklist and summary, sample telemetry in
both CSV schemas, and runnable analysis tooling.

Still to come:

- a drawn wiring diagram (the wiring is currently documented as tables)
- release notes for future public milestones
- a short project demo video

