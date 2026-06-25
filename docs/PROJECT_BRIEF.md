# Project Brief

## Project identity

**Project:** Soft Robotic Glove Controller  
**Institution:** Sultan Qaboos University  
**Domain:** Mechatronics, embedded systems, feedback control, and electropneumatics  
**Portfolio scope:** Public summary of a bench-stage engineering prototype

---

## Problem

A soft pneumatic glove controller must make motion measurable, controllable, repeatable, and observable.

The controller reads finger-bending feedback, computes a command from the angle error, drives pump hardware, routes airflow through a shared manifold, and records telemetry for bench analysis.

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

This branch is intentionally readable and avoids unnecessary complexity.

---

## Contribution focus

This portfolio highlights work in embedded firmware, pneumatic valve logic, motor-driver interfacing, sensor calibration, serial telemetry, hardware bring-up planning, and engineering documentation.
