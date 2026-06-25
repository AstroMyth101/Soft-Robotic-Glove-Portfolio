# Validation Checklist

Source reference: `AlternativeController.ino` / `VAA0.0.5.2_Mega2560_SimpleRefined`

Board: Arduino Mega 2560  
Stage: bench-validation prototype  
Firmware style: minimal proportional controller

---

## 1. Software compile check

| Check | Expected result | Pass |
|---|---|---|
| Open sketch in Arduino IDE | Sketch loads without missing tabs | [ ] |
| Select board | Arduino Mega or Mega 2560 | [ ] |
| Select port | Correct USB serial port | [ ] |
| Compile | No errors | [ ] |
| Upload | Upload completes | [ ] |

Notes:

```text
Board: Arduino Mega 2560
Baud: 115200
Line ending: Newline or Both NL & CR
```

---

## 2. Startup safe-state check

Perform with actuator power disconnected first.

| Output | Pin | Expected startup command | Pass |
|---|---:|---|---|
| Central 3/2 valve | D22 | OFF / vacuum-opening path | [ ] |
| Finger valve 1 | D23 | OFF / open flow | [ ] |
| Finger valve 2 | D24 | OFF / open flow | [ ] |
| Finger valve 3 | D25 | OFF / open flow | [ ] |
| Finger valve 4 | D26 | OFF / open flow | [ ] |
| Finger valve 5 | D27 | OFF / open flow | [ ] |
| Pressure pump PWM | D5 | 0 PWM | [ ] |
| Vacuum pump PWM | D6 | 0 PWM | [ ] |

The firmware calls `stopAllActuatorsSafe()` during startup and whenever the controller is not running.

---

## 3. Serial interface check

Open Serial Monitor at `115200` baud.

| Command | Expected response | Pass |
|---|---|---|
| `VERSION` | Firmware identity printed | [ ] |
| `PINS` | Mega 2560 pin map printed | [ ] |
| `VALVES` | Valve truth table and current commands printed | [ ] |
| `GAINS` | Pressure and vacuum gains printed | [ ] |
| `RAW` | Raw flex readings and angles printed | [ ] |
| `HELP` | Command list printed | [ ] |

---

## 4. Sensor check

| Sensor | Pin | Expected behavior | Pass |
|---|---:|---|---|
| Flex 1 | A0 | Raw value changes when bent | [ ] |
| Flex 2 | A1 | Raw value changes when bent | [ ] |
| Flex 3 | A2 | Raw value changes when bent | [ ] |
| Flex 4 | A3 | Raw value changes when bent | [ ] |
| Flex 5 | A4 | Raw value changes when bent | [ ] |

Use:

```text
RAW
```

Then gently bend each sensor and confirm only the expected channel changes strongly.

---

## 5. Calibration check

| Step | Command | Expected result | Pass |
|---|---|---|---|
| Capture open pose | `CALOPEN` | Current pose stored as 0 degrees | [ ] |
| Capture flex pose | `CALFLEX` | Current pose stored as 80 degrees | [ ] |
| Show arrays | `CALSHOW` | `rawOpen` and `rawFlex` arrays printed | [ ] |
| Verify live angles | `RAW` | Angles stay inside 0 to 80 degrees | [ ] |

Calibration must be repeated when sensor placement, divider wiring, or glove geometry changes.

---

## 6. LCD and I2C check

| Device | Address | Expected result | Pass |
|---|---:|---|---|
| 16x2 LCD | `0x27` | Startup text and live status shown | [ ] |
| MPU6050 | `0x68` | Detected if installed; zeros if absent | [ ] |

The firmware uses Mega hardware I2C:

```text
SDA = D20
SCL = D21
```

---

## 7. Driver-input check before loads

Use a meter, LED tester, or logic probe before connecting loads.

| Test | Expected result | Pass |
|---|---|---|
| `START` with target above measured angle | D22 selects pressure path; D5 PWM becomes active | [ ] |
| `START` with target below measured angle | D22 selects vacuum path; D6 PWM becomes active | [ ] |
| Error inside deadband | Both pump PWM outputs remain off | [ ] |
| `STOP` | D5/D6 return to 0 and valves return to safe bench state | [ ] |

---

## 8. Pneumatic bench check

Use short tests and a loose actuator only.

| Check | Expected result | Pass |
|---|---|---|
| Pressure path | Actuator flexes when pressure command is active | [ ] |
| Vacuum path | Actuator opens when vacuum command is active | [ ] |
| Finger isolation during pressure | Completed fingers close their 2/2 valves | [ ] |
| Vacuum motion | Finger valves remain open | [ ] |
| STOP command | Pumps stop and central valve returns to vacuum/opening path | [ ] |

---

## 9. CSV logging check

The firmware prints one CSV header and then data rows every 100 ms.

Expected columns:

```text
t_ms,target,kp_pressure,kp_vacuum,f1,f2,f3,f4,f5,avg,error,mode,pump_pwm,central_pressure,f1_closed,f2_closed,f3_closed,f4_closed,f5_closed,ax,ay,az,gx,gy,gz
```

| Check | Expected result | Pass |
|---|---|---|
| Header appears once at startup | Column names printed | [ ] |
| Data rows stream continuously | One row every 100 ms approximately | [ ] |
| Lines beginning with `#` | Diagnostic/comment lines only | [ ] |
| CSV rows | No `#` prefix | [ ] |

---

## 10. Review result

| Gate | Result | Notes |
|---|---|---|
| Software compile | [ ] Pass / [ ] Fail |  |
| Bench electronics | [ ] Pass / [ ] Fail |  |
| Sensors and calibration | [ ] Pass / [ ] Fail |  |
| Driver signals | [ ] Pass / [ ] Fail |  |
| Pneumatic bench | [ ] Pass / [ ] Fail |  |
