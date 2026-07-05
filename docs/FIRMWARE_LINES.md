# Firmware Lines

The project maintains several firmware lines with different goals. The public
portfolio documents them at architecture level; full sources live in the
private development repository (see
[`PRIVATE_REPO_POLICY.md`](PRIVATE_REPO_POLICY.md)).

| Line | Board | Firmware identity | Control | Status |
|---|---|---|---|---|
| **Bench-validated baseline** | Arduino Mega 2560 | `VAA0.0.5.2_Mega2560_SimpleRefined` | Proportional-only, average-angle | **Bench-validated** (Levels 1–3) |
| **Full controller** | ESP32-S3-WROOM-2-N32R16V | `V008.7.1` | FSM + PI, latched faults | Development / reference |
| **Simplified** | ESP32-S3-WROOM-2-N32R16V | `VAA0.0.4.4_MinimalProportional_ValveTruthTablePatch` | Proportional-only, average-angle | Bench branch |
| **ESP32 classic port** | ESP32-WROOM-32 DevKit (38-pin) | deterministic build (no discrete version string) | FSM + PI (5-state) | Port of the FSM baseline |
| **Legacy** | ESP32-S3 | legacy proportional line | Proportional, worst-unfinished-finger | Superseded |

---

## Bench-validated baseline — Arduino Mega 2560

`VAA0.0.5.2_Mega2560_SimpleRefined` is the line all bench validation claims
refer to. Proportional-only control on the average glove angle, direction
selected by the sign of the error, per-finger isolation during flexion, USB
serial CSV telemetry (25 columns), 16x2 I2C LCD, optional MPU6050. Kept
deliberately minimal: no Wi-Fi, no SD, no fault framework beyond a safe stop.

Documented in this repository:
[`PIN_MAP_MEGA2560.md`](PIN_MAP_MEGA2560.md) ·
[`CONTROL_STRATEGY.md`](CONTROL_STRATEGY.md) ·
[`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md) ·
[`CALIBRATION_WORKSHEET.md`](CALIBRATION_WORKSHEET.md) ·
[`../firmware_snippets/control_loop_excerpt.cpp`](../firmware_snippets/control_loop_excerpt.cpp)

## Full controller — ESP32-S3

`V008.7.1` is the structured research controller: cooperative scheduler,
7-state FSM, per-direction PI with anti-windup, latched fault model
(5 fault reasons), over-flex and sensor-plausibility guards, task watchdog and
brownout supervision, microSD session logging, Wi-Fi dashboard, and a ~40
command serial CLI. Described in
[`ESP32S3_CONTROLLER_OVERVIEW.md`](ESP32S3_CONTROLLER_OVERVIEW.md), with a code
excerpt in
[`../firmware_snippets/esp32s3_state_machine_excerpt.cpp`](../firmware_snippets/esp32s3_state_machine_excerpt.cpp).

## Simplified — ESP32-S3

`VAA0.0.4.4_MinimalProportional_ValveTruthTablePatch` carries the same minimal
proportional control law as the Mega baseline onto the ESP32-S3 (same
25-column CSV schema), with all fault/FSM/SD/Wi-Fi machinery intentionally
removed. Used for like-for-like control-law comparison across boards.

## ESP32 classic port — ESP32-WROOM-32

A preserved-architecture port of the FSM controller to the classic 38-pin
ESP32 DevKit (5-state FSM: no angle-setpoint mode). Same 20-column CSV schema
and safety model as the full controller; different pin map.

## Legacy — ESP32-S3

The earlier extensible bench-test proportional line (worst-unfinished-finger
command, feature-switched LCD/CSV/IMU hooks). Superseded by the lines above;
retained for history.

---

## Calibration firmware

A dedicated calibration sketch line (`ESP32-S3_FlexCalibration`, pin-matched to
the `V008.7` GPIO map) forces all actuators off, captures open / flexed /
safe-limit poses with multi-frame averaging and spread warnings, and prints
ready-to-paste calibration constants. The Mega baseline instead calibrates
in-firmware via serial commands — see
[`CALIBRATION_WORKSHEET.md`](CALIBRATION_WORKSHEET.md).

---

## Version naming

Firmware identity strings are embedded in each sketch header and printed at
boot (`VERSION` / boot banner), rather than relying on repository tags. Two
families exist historically: `VAAx.x.x_*` (minimal proportional lines) and
`V00x.x` (structured FSM controller line).
