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

Valid control must respect the pneumatic hardware. The software cannot create hardware channels that do not exist.

---

## Why proportional-only was used

The proportional branch was made for clear bench demonstration:

- easy to explain
- easy to tune
- easy to debug
- lightweight on an Arduino Mega 2560
- suitable for showing target-angle feedback behavior

More advanced branches can add PI/PID, pressure sensors, filtered estimation, or model-based control later. The simple branch keeps the first principle visible.
