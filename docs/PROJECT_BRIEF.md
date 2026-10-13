# Project Brief

## Project identity

**Project:** Soft Robotic Glove Controller  
**Institution:** Sultan Qaboos University  
**Domain:** Mechatronics, embedded systems, feedback control, and electropneumatics  
**Portfolio scope:** Public summary of a bench-stage engineering prototype

---

## Problem

The controller estimates finger angles using flex sensors and adjusts a shared pressure/vacuum circuit in response to angle error. Serial telemetry supports bench inspection and analysis.

---

## Engineering objectives

1. Accept a target finger angle.
2. Estimate finger angles from flex-sensor readings.
3. Generate a proportional command from angle error.
4. Drive pressure or vacuum pump hardware through motor drivers.
5. Select the pneumatic path using a central selector valve.
6. Gate individual fingers using finger isolation valves.
7. Show status on an LCD and stream serial telemetry.
8. Preserve clear wiring and validation documentation.

---

## Current public baseline

The public baseline is the **minimal Arduino Mega 2560 proportional controller**.

It demonstrates the core loop:

```text
angle target -> measured angle -> proportional error -> actuator command
```

The baseline excludes the ESP32-S3 line's scheduler, logging, and fault-management features.

