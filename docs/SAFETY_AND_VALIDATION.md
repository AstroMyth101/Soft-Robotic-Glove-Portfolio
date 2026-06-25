# Safety and Validation

## Validation status

This portfolio documents a **bench-stage engineering prototype**. The repository is intended for project review, learning, and engineering demonstration.

It is not a product release.

---

## Validation levels

| Level | Meaning | Status in this portfolio |
|---|---|---|
| Level 1 | Software review, compile, static inspection | Required before upload |
| Level 2 | Bench electronics, actuator power disconnected | Primary early test stage |
| Level 3 | Pneumatic bench, no hand attached | Required before integrated tests |
| Level 4 | Integrated glove on bench | Later engineering validation |
| Level 5 | Use beyond bench validation | Not covered by this repository |

---

## Minimum bench discipline

Before applying actuator power:

1. Confirm the microcontroller uploads correctly.
2. Confirm all GPIO outputs begin in the expected safe state.
3. Confirm LCD and Serial output.
4. Confirm sensor readings are reasonable.
5. Confirm pump-driver inputs using a meter or logic probe.
6. Confirm valve-driver inputs before connecting valve loads.
7. Test pumps and valves separately.
8. Test the pneumatic path on a loose actuator only.
9. Stop immediately if behavior does not match the expected state table.

---

## Hardware protection expected for serious testing

A serious pneumatic test setup should include:

- pressure regulation
- over-pressure relief
- vacuum limiting
- current limiting or fusing
- flyback diodes across inductive loads
- MOSFET gate pull-down resistors
- rated wiring and connectors
- a physical way to cut actuator power quickly

Software is only one protection layer. Hardware must be able to fail safely.

---

## Known bench risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Floating MOSFET gates | Actuators may switch unexpectedly | Gate pull-down resistors |
| Wrong valve polarity | Pressure/vacuum path may invert | Validate with low-risk bench tests |
| Pump-driver DIR floating | Pump direction may be wrong | Tie DIR pins to defined logic level |
| Sensor miscalibration | Controller may drive in the wrong direction or overdrive | Calibrate open and flex poses |
| Shared pneumatic path | Independent finger pressure is not possible | Use isolation logic only |
| Sustained pump command | Pressure may build during a stalled motion | Use limits, short tests, and external protection |

---

## Safe bring-up order

```text
USB upload
-> Serial output
-> GPIO outputs
-> LCD
-> flex sensors
-> buttons / commands
-> driver inputs
-> valve loads
-> pump loads
-> pneumatic path
-> integrated bench test
```

Do not jump straight to full-system operation. That is how debugging becomes archaeology.
