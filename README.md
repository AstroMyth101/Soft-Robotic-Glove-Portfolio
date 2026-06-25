# Soft Robotic Glove Portfolio

Public engineering portfolio for a **soft robotic glove controller** developed at **Sultan Qaboos University (SQU)**.

This repository summarizes the system architecture, control concept, wiring, validation workflow, and documentation style for a bench-stage electropneumatic controller project.

> **Status:** Bench-validation engineering prototype  
> **Primary focus:** Embedded control, electropneumatic actuation, sensor feedback, and engineering documentation

---

## What this project does

The controller drives a five-finger soft pneumatic glove using:

- flex-sensor feedback for finger angle estimation
- a shared pressure/vacuum pneumatic path
- a central 3/2 pressure-vacuum selector valve
- five normally-open 2/2 finger isolation valves
- pressure and vacuum pumps driven through motor-driver hardware
- serial telemetry and LCD feedback in the minimal bench branch
- richer ESP32/ESP32-S3 firmware lines for logging, Wi-Fi, dashboard, and safety architecture work

The core engineering loop is:

```text
target angle -> flex sensor feedback -> control command -> pneumatic actuation -> measured angle
```

---

## Repository map

| Path | Purpose |
|---|---|
| [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) | High-level problem, scope, requirements, and contribution summary |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System modules, software structure, and data/control flow |
| [`docs/CONTROL_STRATEGY.md`](docs/CONTROL_STRATEGY.md) | Proportional control concept and shared-air pneumatic limitations |
| [`docs/SAFETY_AND_VALIDATION.md`](docs/SAFETY_AND_VALIDATION.md) | Safety boundaries, validation levels, and bring-up sequence |
| [`docs/VALIDATION_CHECKLIST.md`](docs/VALIDATION_CHECKLIST.md) | Bench checklist derived from the current controller firmware |
| [`docs/CALIBRATION_WORKSHEET.md`](docs/CALIBRATION_WORKSHEET.md) | Flex-sensor calibration worksheet for the Mega 2560 branch |
| [`docs/PIN_MAP_MEGA2560.md`](docs/PIN_MAP_MEGA2560.md) | Public wiring summary for the minimal Arduino Mega 2560 branch |
| [`samples/sample_serial_log.csv`](samples/sample_serial_log.csv) | Representative serial CSV sample using the current firmware schema |
| [`firmware_snippets/control_loop_excerpt.cpp`](firmware_snippets/control_loop_excerpt.cpp) | Public-safe excerpt of the proportional control loop |
| [`docs/LIMITATIONS_AND_FUTURE_WORK.md`](docs/LIMITATIONS_AND_FUTURE_WORK.md) | Known limitations and planned engineering upgrades |
| [`docs/PRIVATE_REPO_POLICY.md`](docs/PRIVATE_REPO_POLICY.md) | What is intentionally not included here and why |
| [`CHANGELOG.md`](CHANGELOG.md) | Public portfolio change history |

---

## Current public baseline

The public documentation focuses on the **minimal proportional bench controller** line:

```text
Firmware VAA0.0.5.2_Mega2560_SimpleRefined
Controller: Arduino Mega 2560
Control: proportional-only, average-angle feedback
Telemetry: USB Serial CSV + 16x2 I2C LCD + optional MPU6050
```

This line was kept intentionally simple for demonstration and bench validation. It is not the full feature-rich ESP32-S3 research controller.

---

## Pneumatic reality

The current pneumatic hardware uses a shared pressure/vacuum source. That means the system can:

- inflate connected fingers together
- vacuum connected fingers together
- isolate individual fingers after they reach target
- continue moving unfinished fingers while completed fingers are closed off

It cannot:

- inflate one finger while vacuuming another
- regulate independent pressure for each finger
- estimate force from flex sensors alone

This distinction matters. A controller that ignores the pneumatic hardware is not a controller; it is fiction with GPIO pins.

---

## Skills demonstrated

This portfolio demonstrates practical work in:

- embedded C/C++ firmware design
- Arduino / ESP32 / ESP32-S3 / AVR-style development
- finite-state control concepts
- proportional feedback control
- pneumatic actuation and valve logic
- sensor calibration and signal interpretation
- serial telemetry and bench logging
- wiring documentation and validation planning
- engineering communication

---

## Author

**Rashid Al-Ma'awali**  
Mechatronics Engineering Student, Sultan Qaboos University  
GitHub: [AstroMyth101](https://github.com/AstroMyth101)
