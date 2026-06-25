# Arduino Mega 2560 Pin Map

Public wiring summary for the minimal proportional controller branch:

```text
Firmware: VAA0.0.5.2_Mega2560_SimpleRefined
Board: Arduino Mega 2560
```

Wire by **pin label / signal name**, not by guesswork.

---

## Main connections

| Subsystem | Code symbol | Mega 2560 pin | I/O type | Connection target | Active logic / notes |
|---|---|---:|---|---|---|
| Central selector valve | `PIN_CENTRAL_VALVE` | D22 | Digital output | Central 3/2 valve input | LOW = vacuum/opening path, HIGH = pressure/flexion path |
| Finger valve 1 | `PIN_FINGER_VALVE[0]` | D23 | Digital output | Finger 1 2/2 valve input | LOW = open flow, HIGH = closed/isolated |
| Finger valve 2 | `PIN_FINGER_VALVE[1]` | D24 | Digital output | Finger 2 2/2 valve input | LOW = open flow, HIGH = closed/isolated |
| Finger valve 3 | `PIN_FINGER_VALVE[2]` | D25 | Digital output | Finger 3 2/2 valve input | LOW = open flow, HIGH = closed/isolated |
| Finger valve 4 | `PIN_FINGER_VALVE[3]` | D26 | Digital output | Finger 4 2/2 valve input | LOW = open flow, HIGH = closed/isolated |
| Finger valve 5 | `PIN_FINGER_VALVE[4]` | D27 | Digital output | Finger 5 2/2 valve input | LOW = open flow, HIGH = closed/isolated |
| Pressure pump driver | `PIN_PRESSURE_PWM` | D5 | PWM output | Cytron MDD10A pressure PWM input | `analogWrite()` 0..255; DIR tied to GND |
| Vacuum pump driver | `PIN_VACUUM_PWM` | D6 | PWM output | Cytron MDD10A vacuum PWM input | `analogWrite()` 0..255; DIR tied to GND |
| Flex sensor 1 | `PIN_FLEX[0]` | A0 / D54 | Analog input | Finger 1 flex divider output | Mega ADC 0..1023 |
| Flex sensor 2 | `PIN_FLEX[1]` | A1 / D55 | Analog input | Finger 2 flex divider output | Mega ADC 0..1023 |
| Flex sensor 3 | `PIN_FLEX[2]` | A2 / D56 | Analog input | Finger 3 flex divider output | Mega ADC 0..1023 |
| Flex sensor 4 | `PIN_FLEX[3]` | A3 / D57 | Analog input | Finger 4 flex divider output | Mega ADC 0..1023 |
| Flex sensor 5 | `PIN_FLEX[4]` | A4 / D58 | Analog input | Finger 5 flex divider output | Mega ADC 0..1023 |
| I2C SDA | `Wire.begin()` | D20 / SDA | I2C | LCD and optional MPU6050 | Hardware I2C |
| I2C SCL | `Wire.begin()` | D21 / SCL | I2C | LCD and optional MPU6050 | Hardware I2C |

---

## I2C devices

| Device | I2C address | Mega pins | Note |
|---|---:|---|---|
| 16x2 I2C LCD | `0x27` | D20/SDA, D21/SCL | Local status display |
| MPU6050 IMU | `0x68` | D20/SDA, D21/SCL | Optional; acceleration and gyro data if present |

---

## Not used in the minimal branch

| Item | Status |
|---|---|
| SD card | Not used |
| Wi-Fi / WebSocket | Not used |
| Pump DIR pins | Not assigned in firmware; MDD10A DIR pins are tied to GND |
| E-stop button | Not assigned in the minimal branch |
| Mode button | Not assigned in the minimal branch |

---

## Wiring notes

- Do not leave MDD10A DIR inputs floating.
- Do not run pressure and vacuum pumps at the same time.
- Confirm valve logic before connecting pneumatic loads.
- Confirm flex-sensor calibration before relying on angle feedback.
