# Architecture

## High-level system

```mermaid
flowchart LR
    A[Target angle command] --> B[Microcontroller]
    C[Flex sensors] --> B
    B --> D[Pump drivers]
    B --> E[Central selector valve]
    B --> F[Finger isolation valves]
    D --> G[Shared pneumatic manifold]
    E --> G
    F --> H[Soft glove actuators]
    H --> C
    B --> I[USB Serial telemetry]
    B --> J[16x2 I2C LCD]
```

---

## Hardware modules

| Module | Role |
|---|---|
| Microcontroller | Reads sensors, computes control command, drives outputs |
| Flex sensors | Estimate finger bending angle |
| Pump drivers | Drive pressure and vacuum pump channels |
| Central selector valve | Selects pressure or vacuum path for the shared manifold |
| Finger valves | Open or isolate each finger channel |
| LCD | Local status display |
| USB Serial | Commands, CSV telemetry, debugging |
| Optional IMU | Extra motion data when connected |

---

## Pneumatic architecture

One shared pressure path and one shared vacuum path serve all five fingers.
The central 3/2 valve selects which source feeds the shared manifold; each
finger has a normally-open 2/2 isolation valve between the manifold and its
actuator.

```mermaid
flowchart LR
    PP[Pressure pump] --> CV{Central 3/2 valve}
    VP[Vacuum pump] --> CV
    CV --> M[Shared manifold]
    M --> V1[2/2 valve F1] --> A1[Finger 1 actuator]
    M --> V2[2/2 valve F2] --> A2[Finger 2 actuator]
    M --> V3[2/2 valve F3] --> A3[Finger 3 actuator]
    M --> V4[2/2 valve F4] --> A4[Finger 4 actuator]
    M --> V5[2/2 valve F5] --> A5[Finger 5 actuator]
```

### Valve truth table

| Valve | Command LOW / OFF | Command HIGH / ON |
|---|---|---|
| Central 3/2 selector | Vacuum / opening path | Pressure / flexion path |
| Finger 2/2 (normally open) | Open flow | Closed / isolated |

Two consequences follow directly from this hardware:

1. De-energizing selects the vacuum path and opens the finger isolation valves.
   Actual pressure relief must be verified on the assembled pneumatic circuit.
2. The controller can isolate fingers that reached their target, but it cannot
   inflate one finger while vacuuming another or regulate per-finger pressure.

---

## Minimal controller data flow

```text
1. Read five flex sensors.
2. Convert each raw reading into an angle estimate.
3. Compute the average glove angle.
4. Compare average angle with target angle.
5. Apply proportional control.
6. Select pressure, vacuum, or hold mode.
7. Update pump PWM and valve states.
8. Stream telemetry.
```

---

## Firmware style

The Mega 2560 baseline excludes:

- no Wi-Fi
- no WebSocket dashboard
- no SD card logging
- no FreeRTOS task split
- no PID or PI loop
- no large fault framework

The ESP32-S3 line adds a scheduler, state machine, fault handling, logging, and a dashboard. See [`ESP32S3_CONTROLLER_OVERVIEW.md`](ESP32S3_CONTROLLER_OVERVIEW.md).

