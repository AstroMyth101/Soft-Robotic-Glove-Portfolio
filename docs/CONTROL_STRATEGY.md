# Control Strategy

## Public baseline

The public baseline uses **proportional-only angle control**.

There is one common target angle for the glove. The firmware reads five flex sensors, estimates each finger angle, computes the average glove angle, and drives the shared pneumatic system based on the average error.

```text
error = target_angle - average_angle
command = Kp * abs(error)
```

A deadband prevents unnecessary pump activity near the target.

---

## Mode selection

| Error condition | Controller action |
|---|---|
| `error > deadband` | Select pressure path and drive pressure pump |
| `error < -deadband` | Select vacuum path and drive vacuum pump |
| `abs(error) <= deadband` | Stop both pumps and hold position |

The pressure and vacuum gains are separate because the two directions usually respond differently.

---

## Finger valve logic

During pressure motion, a finger that reaches the target region can be isolated while slower fingers remain connected.

During vacuum motion, the minimal branch keeps all finger valves open so the glove returns together.

This is not independent pressure control. The valves act as isolation gates, not precision pressure regulators.

---

## Shared-air limitation

The hardware has one shared pressure path and one shared vacuum path. Because of that, the controller cannot:

- pressure one finger while vacuuming another
- apply a different pressure to each finger
- infer contact force from flex readings alone

Valve isolation does not provide independent pressure regulation.

---

## Control trade-off

The Mega 2560 branch uses proportional control to establish a simple bench reference. Its steady-state error and response depend on the pneumatic plant and gain settings; the ESP32-S3 line implements PI control with anti-windup.
