# Flex Sensor Calibration Worksheet

Source reference: `AlternativeController.ino` / `VAA0.0.5.2_Mega2560_SimpleRefined`

This worksheet documents the calibration flow used by the current minimal Arduino Mega 2560 controller.

---

## Calibration model

Each finger uses a linear mapping between two poses:

| Pose | Meaning | Firmware command |
|---|---|---|
| Open pose | 0 degrees | `CALOPEN` |
| Flexed pose | 80 degrees | `CALFLEX` |

The firmware maps raw ADC values to angle using:

```text
angle = (raw - rawOpen) * 80 / (rawFlex - rawOpen)
```

The reported angle is constrained to the 0 to 80 degree range.

---

## Firmware defaults

The current firmware contains measured placeholder arrays:

```cpp
rawOpen = {556, 560, 617, 463, 725};
rawFlex = {765, 746, 750, 699, 919};
```

These values are hardware-specific. Recalibrate after any sensor remounting or wiring change.

---

## Before calibration

| Check | Expected result | Pass |
|---|---|---|
| Mega connected over USB | Serial Monitor opens at 115200 baud | [ ] |
| Flex sensors connected | A0 to A4 respond to bending | [ ] |
| Actuator power disconnected | No pneumatic motion during calibration | [ ] |
| Serial line ending | Newline or Both NL & CR | [ ] |
| `RAW` command tested | Raw values visible | [ ] |

---

## Step 1: open pose capture

Place all fingers in the open reference pose.

Send:

```text
CALOPEN
```

Record the printed values:

| Finger | Pin | Raw open value |
|---|---:|---:|
| F1 | A0 |  |
| F2 | A1 |  |
| F3 | A2 |  |
| F4 | A3 |  |
| F5 | A4 |  |

---

## Step 2: flex pose capture

Place all fingers at the selected flex reference pose.

Send:

```text
CALFLEX
```

Record the printed values:

| Finger | Pin | Raw flex value | Span = flex - open | Span OK? |
|---|---:|---:|---:|---|
| F1 | A0 |  |  | [ ] |
| F2 | A1 |  |  | [ ] |
| F3 | A2 |  |  | [ ] |
| F4 | A3 |  |  | [ ] |
| F5 | A4 |  |  | [ ] |

The firmware warns if the span is too small.

---

## Step 3: verify live angle output

Send:

```text
RAW
```

Check that each channel reports sensible angle values.

| Test pose | Expected angle range | Pass |
|---|---|---|
| Open pose | near 0 degrees | [ ] |
| Mid pose | between 0 and 80 degrees | [ ] |
| Flex pose | near 80 degrees | [ ] |

---

## Step 4: optional one-point estimate

For a known intermediate pose, use:

```text
CAL <angle>
```

Example:

```text
CAL 40
```

This estimates open and flex references from the current raw readings and the known angle.

Use two-point calibration with `CALOPEN` and `CALFLEX` when possible. It is more direct.

---

## Step 5: final calibration record

Final values to copy into firmware if needed:

```cpp
static int rawOpen[NUM_FINGERS] = {___, ___, ___, ___, ___};
static int rawFlex[NUM_FINGERS] = {___, ___, ___, ___, ___};
```

---

## Calibration notes

- The Arduino Mega ADC range is 0 to 1023.
- Flex readings depend on divider resistor values and sensor placement.
- Do not compare ESP32-S3 raw ADC values directly with Mega ADC values.
- Recalibrate whenever the glove, sensor tape, wiring, or board changes.
