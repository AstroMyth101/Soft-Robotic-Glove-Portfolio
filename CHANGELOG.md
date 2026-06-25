# Changelog

This changelog tracks the public portfolio repository, not the full private firmware history.

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
