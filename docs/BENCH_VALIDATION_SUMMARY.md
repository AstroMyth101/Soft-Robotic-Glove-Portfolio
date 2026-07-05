# Bench Validation Summary

Public summary of the bench-validation status of the current baseline. Adapted
from the internal validation record in the private development repository.

```text
Firmware identity: VAA0.0.5.2_Mega2560_SimpleRefined
Board: Arduino Mega 2560
Validation scope: Bench validation only
Human testing: NOT APPROVED
```

## Verdict

The Arduino Mega 2560 minimal proportional branch is the current
bench-validated baseline. It has demonstrated the core control chain on real
bench hardware:

```text
target angle -> flex sensor feedback -> average glove angle
  -> proportional command -> pressure/vacuum actuation -> Serial/LCD telemetry
```

This does **not** mean the system is clinically safe, medically approved,
patient-ready, or approved for human testing.

## Validation level

| Level | Meaning | Status |
|---|---|---|
| Level 1 | Static review / compilation / upload preparation | Completed for this branch |
| Level 2 | Bench electronics | Demonstrated |
| Level 3 | Pneumatic bench testing | Demonstrated |
| Level 4 | Integrated bench reliability | Not fully validated |
| Level 5 | Human testing | **NOT APPROVED** |

Compilation, upload, telemetry, or actuator motion alone do not prove safety.

## What was validated

1. **Firmware runs on Arduino Mega 2560 hardware** — starts correctly, USB
   serial interface available, commands accepted, firmware identity printable.
2. **Flex sensors were calibrated** using the built-in serial workflow
   (`CALOPEN` / `CALFLEX` / `RAW`); open and flexed references captured, raw
   and computed angles inspectable, average glove angle computed from five
   fingers. Calibration is hardware-specific and must not be reused blindly.
3. **LCD and serial telemetry work** — serial CLI, CSV telemetry, `#`
   diagnostic lines, and 16x2 I2C LCD output.
4. **Pressure and vacuum actuation were demonstrated** — pump drivers receive
   PWM (D5 pressure, D6 vacuum, Cytron MDD10A, DIR hardwired to GND), pumps
   never commanded simultaneously, proportional PWM tracks angle error. This
   proves bench actuator response, not clinical safety.
5. **Central 3/2 valve behavior was confirmed** — LOW = vacuum/opening path,
   HIGH = pressure/flexion path; shared by all fingers.
6. **Finger valve behavior was confirmed** — normally-open 2/2 valves;
   LOW = open flow, HIGH = closed/isolated; open together during vacuum,
   individually closable during pressure.
7. **Safe bench stop state was demonstrated** — pumps off, central valve to
   vacuum/opening path, all finger valves open. A useful bench behavior, not a
   substitute for hardware safety devices.
8. **Bench logs exist** and are tied to the firmware identity printed inside
   each log (a representative sample is committed at
   [`../samples/sample_serial_log.csv`](../samples/sample_serial_log.csv)).

## What was NOT validated

1. **Clinical safety** — the system is not clinically safe, medically
   approved, or patient-ready. No document in this repository claims otherwise.
2. **Human testing** — NOT APPROVED. The glove must not be used on a person
   based on this firmware or the available logs.
3. **Long-term reliability** — long-duration cycling, pump/valve/driver
   thermal behavior, tubing and actuator fatigue, sensor drift, calibration
   stability, wiring vibration, repeated power cycling.
4. **Pressure and vacuum safety limits** — no validated maximum pressure or
   vacuum limits; regulator, relief valves, actuator-power E-stop, current
   protection, rated wiring, and formal approval are still required before any
   human-related test planning.
5. **Fault-injection behavior** — stuck valves, blocked lines, disconnected or
   shorted sensors, driver faults, brownout, overpressure/over-pull, operator
   mistakes, emergency-stop behavior. (The minimal Mega branch intentionally
   does not carry the full ESP32-S3 safety architecture.)
6. **Independent per-finger pressure control** — the shared pneumatic path
   cannot inflate one finger while vacuuming another, cannot regulate
   per-finger pressure or vacuum, and cannot estimate contact force from flex
   sensors alone.

## Interpretation

Use this baseline as: a known working reference, a hardware validation
checkpoint, a simple demonstration branch, a calibration and actuator-test
reference, and a comparison point for the ESP32-S3 work.

Do not use it as: a clinical controller, a final safety architecture, evidence
of human-readiness, or proof of long-term reliability or pneumatic safety.

Evidence from this branch and evidence from the ESP32-S3 full controller are
kept separate; validation claims are always tied to a specific firmware
identity.
