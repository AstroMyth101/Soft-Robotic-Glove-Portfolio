# Changelog

This changelog tracks the public portfolio repository, not the full private firmware history.

---

## 2026-07-05

### Added

- ESP32-S3 full controller overview (`docs/ESP32S3_CONTROLLER_OVERVIEW.md`): FSM state diagram, PI control, latched fault model, safety layers, 20-column CSV schema.
- Firmware-lines comparison document (`docs/FIRMWARE_LINES.md`).
- Public bench-validation summary (`docs/BENCH_VALIDATION_SUMMARY.md`) with the L1–L5 status ladder.
- Public-safe ESP32-S3 firmware excerpt (`firmware_snippets/esp32s3_state_machine_excerpt.cpp`): state machine, fault latch, safe-relief state, sensor safety guard.
- Representative dummy ESP32-S3 session log (`samples/sample_esp32s3_session_log.csv`, 20-column schema).
- Runnable host-side tooling under `tools/`: CSV schema validator, per-finger step-response analyzer, and five-finger control-law simulator, with usage documentation (`tools/README.md`). Sanitized public copies of the private bench tooling.
- Pneumatic architecture diagram and valve truth table in `docs/ARCHITECTURE.md`.

### Changed

- README: banner image, explicit "human testing NOT APPROVED" status, firmware-lines table, runnable-evidence section, validation snapshot, expanded repository map.
- `docs/LIMITATIONS_AND_FUTURE_WORK.md`: delivered items (diagrams, state diagram, samples, excerpts, worksheet, validation summary, tooling) marked done; remaining work kept open.

### Fixed

- `.gitignore` no longer ignores the curated sample logs (`!samples/*.csv` exception; the blanket `*.csv` rule previously excluded new sample files).
- Banner asset renamed (`linkedin-thumbnai.png` → `linkedin-thumbnail.jpg`) and recompressed from 1.9 MB to ~0.3 MB.

### Current public firmware references

```text
VAA0.0.5.2_Mega2560_SimpleRefined  (bench-validated baseline, Arduino Mega 2560)
V008.7.1                           (full controller, ESP32-S3, development/reference)
```

---

## 2026-06-25

### Added

- Public project README.
- Project brief.
- Architecture document with system data flow.
- Control strategy document for the proportional branch.
- Safety and validation document.
- Arduino Mega 2560 pin map.
- Limitations and future work document.
- Private repository policy.
- Validation checklist derived from the current controller firmware.
- Flex sensor calibration worksheet derived from the current controller firmware.
- Sample serial CSV log with representative dummy data.
- Public control-loop firmware excerpt.

### Current public firmware reference

```text
VAA0.0.5.2_Mega2560_SimpleRefined
```

### Current public baseline summary

- Board: Arduino Mega 2560.
- Control: proportional-only average-angle controller.
- Sensors: five flex sensors on A0 to A4.
- Valves: central selector on D22, finger valves on D23 to D27.
- Pumps: pressure PWM on D5, vacuum PWM on D6.
- Interface: USB Serial CSV and 16x2 I2C LCD.
- Optional: MPU6050 on I2C address 0x68.

---

## Notes

This repository is a curated public portfolio layer. The full development repository remains separate.
