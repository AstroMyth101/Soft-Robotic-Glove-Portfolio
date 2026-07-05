# Tools

Host-side Python tooling for the minimal proportional controller line
(`VAA0.0.5.2_Mega2560_SimpleRefined`). These are sanitized public copies of the
tools used during bench work in the private development repository.

All three run against the sample logs committed in this repository, so the
analysis workflow can be reproduced without any hardware.

**Validation level:** everything here is host-side / Level 1 (software only).
None of these tools prove hardware safety, pneumatic behavior, or clinical
readiness. They describe whatever produced the log.

---

## validate_csv_schema.py

Validates a captured CSV log against the firmware's 25-column CSV contract
(column names, order, field counts, per-column value rules such as
`mode ∈ {P,V,H}` and `pump_pwm ∈ 0..255`).

- Dependencies: Python 3.8+ standard library only.
- Exit codes: `0` pass, `1` validation failure, `2` usage / I/O error.
- Scope: the Mega 2560 25-column schema (`t_ms,...`) only. The ESP32-S3
  session-log schema (`samples/sample_esp32s3_session_log.csv`) is a different
  20-column contract and is documented in
  [`docs/ESP32S3_CONTROLLER_OVERVIEW.md`](../docs/ESP32S3_CONTROLLER_OVERVIEW.md).

```text
python tools/validate_csv_schema.py samples/sample_serial_log.csv
python tools/validate_csv_schema.py --selftest
```

---

## analyze_flex_response.py

Computes per-finger flexion step-response metrics from a captured log:
steady-state error, time-to-band, 10–90% rise time, overshoot %, settling time,
plus per-segment mode fractions (P/V/H) and peak pump PWM. The log is segmented
into steps wherever the operator target changes.

- Dependencies: Python 3.8+ standard library only.
- Output: stdout table, optional `--json` / `--csv` reports.

```text
python tools/analyze_flex_response.py samples/sample_serial_log.csv
python tools/analyze_flex_response.py samples/sample_serial_log.csv --json report.json
python tools/analyze_flex_response.py --selftest
```

---

## soft_robotics_hand_sim.py

Interactive five-finger real-time simulator. The controller half is a faithful
port of the firmware's `updateControl()` (proportional-only, average-angle,
shared pressure/vacuum path, per-finger isolation, safe-stop). The pneumatic
plant half is an illustrative simulation-only model and is clearly labeled as
such in the source.

- Dependencies: Python 3.8+, `numpy` (GUI additionally needs `matplotlib`).
- `--selftest` runs a headless Kp damping sweep with no display required.

```text
python tools/soft_robotics_hand_sim.py            # interactive dashboard
python tools/soft_robotics_hand_sim.py --selftest # headless control-law check
```

---

## Typical workflow

```text
capture serial log  ->  validate_csv_schema.py  ->  analyze_flex_response.py
                          (is the log well-formed?)   (how did the glove respond?)
```

The simulator sits before both: it lets you exercise the same control law and
generate representative behavior without a bench.
