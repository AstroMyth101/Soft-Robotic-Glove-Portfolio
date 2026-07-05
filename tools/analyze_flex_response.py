#!/usr/bin/env python3
"""
analyze_flex_response.py - Per-finger flexion step-response metrics from a captured log.

Target firmware : VAA0.0.5.x_Mega2560 (minimal proportional controller line)
Pairs with      : any raw serial capture of the firmware's 25-column CSV schema
                  (see samples/sample_serial_log.csv in this repository).
                  This tool computes NUMBERS only; it does not plot.
Dependencies     : Python 3.8+ standard library only (no pip, CI-friendly).

VALIDATION LEVEL
  This is an offline analysis utility. It asserts NOTHING about safety, pneumatic
  behaviour, or clinical readiness. The metrics describe whatever produced the log:
  a simulation log is L1; a bench log reflects that bench run but is not, by itself,
  proof of hardware safety or repeatability. Treat the output as engineering data.

WHAT IT MEASURES
  The log is segmented into STEPS wherever the operator target changes value. For
  each step segment, metrics are computed for the controlled variable 'avg' (what
  the firmware actually closes the loop on) and for each finger f1..f5:

    final               last value in the segment (deg)
    sse                 steady-state error = mean(last N samples) - target (deg)
    time_to_band_ms     time from the step until |value - target| first <= deadband
    rise_10_90_ms       time from 10% to 90% of the commanded step (direction-aware)
    overshoot_pct       peak excursion beyond target, in the motion direction,
                        as a percentage of the step magnitude
    settling_ms         time after which the value stays within +/-deadband of
                        target for the rest of the segment ('-' if it never settles)

  Segment-level context (from the firmware's own columns):
    mode fractions      % of segment spent in P / V / H
    peak_pwm            max pump_pwm in the segment

INTERPRETATION NOTE (firmware faithfulness)
  'time_to_band' here uses a SYMMETRIC +/-deadband window around the new target,
  which is the natural response metric. The firmware's per-finger isolation latch
  is ONE-SIDED during flexion (it closes finger i once flexAngle[i] >= target -
  deadband). So do not read 'time_to_band' as the exact valve-close instant; read
  it as "time to reach the target band". The valve-state columns (f*_closed) remain
  the ground truth for actual isolation timing.

PARSING RULES (match the firmware's serial output)
  * '#'-prefixed and blank lines are ignored.
  * Columns are located BY NAME from the header, so extra/renamed columns degrade
    gracefully (a missing finger column is simply skipped).
  * A reprinted header or a backward jump in t_ms starts a new session; steps are
    detected within each session.

EXIT CODES
  0 = ok    1 = self-test failure    2 = usage / I/O error / no usable data

USAGE
  python tools/analyze_flex_response.py samples/sample_serial_log.csv
  python tools/analyze_flex_response.py log.csv --deadband 3.0 --last-n 10 --min-step 5
  python tools/analyze_flex_response.py log.csv --json report.json --csv report.csv
  python tools/analyze_flex_response.py --selftest
"""

from __future__ import annotations

import argparse
import csv as csvmod
import json
import sys
from statistics import fmean
from typing import Dict, List, Optional, Tuple

FINGER_COLS = ["f1", "f2", "f3", "f4", "f5"]
SERIES_ORDER = ["avg"] + FINGER_COLS


# --------------------------------------------------------------------------- #
# Parsing: '#'/blank skip, header-by-name, session split
# --------------------------------------------------------------------------- #
def parse_log(path: str) -> List[Dict[str, List[float]]]:
    """Return a list of sessions; each session is {column_name: [values...]}.

    Non-numeric columns (mode) are kept as strings; numeric columns as floats.
    A new session starts on a reprinted header or a backward t_ms jump.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw_lines = fh.readlines()

    sessions: List[Dict[str, List]] = []
    header: Optional[List[str]] = None
    cur: Optional[Dict[str, List]] = None
    last_t: Optional[float] = None

    def new_session(h: List[str]) -> Dict[str, List]:
        return {name: [] for name in h}

    for raw in raw_lines:
        line = raw.strip()
        if line == "" or line.startswith("#"):
            continue
        fields = [f.strip() for f in line.split(",")]

        if fields and fields[0] == "t_ms":
            header = fields
            cur = new_session(header)
            sessions.append(cur)
            last_t = None
            continue

        if header is None or cur is None:
            continue  # data before any header -> skip silently here
        if len(fields) != len(header):
            continue  # malformed row -> skip (use validate_csv_schema.py to catch)

        # Detect reset-without-header via backward time.
        try:
            t = float(fields[0])
        except ValueError:
            continue
        if last_t is not None and t < last_t:
            cur = new_session(header)
            sessions.append(cur)
        last_t = t

        for name, val in zip(header, fields):
            if name == "mode":
                cur[name].append(val)
            else:
                try:
                    cur[name].append(float(val))
                except ValueError:
                    cur[name].append(float("nan"))

    # Drop empty sessions.
    return [s for s in sessions if s.get("t_ms")]


# --------------------------------------------------------------------------- #
# Metric computation
# --------------------------------------------------------------------------- #
def analyze_series(
    t: List[float],
    x: List[float],
    from_val: float,
    to_val: float,
    deadband: float,
    last_n: int,
) -> Dict[str, Optional[float]]:
    n = len(x)
    res: Dict[str, Optional[float]] = {
        "from": from_val, "to": to_val, "samples": n, "final": None,
        "sse": None, "time_to_band_ms": None,
        "rise_10_90_ms": None, "overshoot_pct": None, "settling_ms": None,
    }
    if n == 0:
        return res

    t0 = t[0]
    res["final"] = x[-1]

    k = min(last_n, n)
    res["sse"] = fmean(x[-k:]) - to_val

    in_band = [abs(v - to_val) <= deadband for v in x]

    for i, ok in enumerate(in_band):
        if ok:
            res["time_to_band_ms"] = t[i] - t0
            break

    last_out = None
    for i, ok in enumerate(in_band):
        if not ok:
            last_out = i
    if last_out is None:
        res["settling_ms"] = 0.0
    elif last_out + 1 < n:
        res["settling_ms"] = t[last_out + 1] - t0
    else:
        res["settling_ms"] = None  # never settles within this segment

    step = to_val - from_val
    if abs(step) >= 1e-6:
        s = 1.0 if step > 0 else -1.0

        def crossed(idx: int, frac: float) -> bool:
            level = from_val + frac * step
            return (x[idx] - level) * s >= 0.0

        t10 = t90 = None
        for i in range(n):
            if t10 is None and crossed(i, 0.10):
                t10 = t[i]
            if t90 is None and crossed(i, 0.90):
                t90 = t[i]
            if t10 is not None and t90 is not None:
                break
        if t10 is not None and t90 is not None and t90 >= t10:
            res["rise_10_90_ms"] = t90 - t10

        peak = max((x[i] - to_val) * s for i in range(n))
        ov = max(peak, 0.0)
        res["overshoot_pct"] = (0.0 if ov == 0.0 else ov / abs(step) * 100.0)

    return res


def detect_steps(target: List[float]) -> List[Tuple[int, int]]:
    """Return (start_idx, end_idx_exclusive) segments split at each target change."""
    n = len(target)
    if n == 0:
        return []
    bounds = [0]
    for i in range(1, n):
        if target[i] != target[i - 1]:
            bounds.append(i)
    bounds.append(n)
    return [(bounds[j], bounds[j + 1]) for j in range(len(bounds) - 1)]


def mode_fractions(modes: List[str]) -> Dict[str, float]:
    n = len(modes)
    if n == 0:
        return {"P": 0.0, "V": 0.0, "H": 0.0}
    out = {m: 0.0 for m in ("P", "V", "H")}
    for m in modes:
        if m in out:
            out[m] += 1.0
    return {m: out[m] / n * 100.0 for m in out}


def analyze_session(
    session: Dict[str, List],
    sess_index: int,
    deadband: float,
    last_n: int,
    min_step: float,
) -> List[dict]:
    t = session.get("t_ms", [])
    target = session.get("target", [])
    if not t or not target:
        return []

    have_fingers = [c for c in FINGER_COLS if c in session]
    have_avg = "avg" in session
    segments = detect_steps(target)

    out: List[dict] = []
    prev_target: Optional[float] = None
    step_no = 0

    for (a, b) in segments:
        to_val = target[a]
        from_val = prev_target if prev_target is not None else to_val
        prev_target = to_val

        seg_t = t[a:b]
        is_step = abs(to_val - from_val) >= max(min_step, 1e-6)
        if is_step:
            step_no += 1

        dur = (seg_t[-1] - seg_t[0]) if len(seg_t) >= 1 else 0.0
        modes = session.get("mode", [])[a:b]
        pwm = session.get("pump_pwm", [])[a:b]
        peak_pwm = max(pwm) if pwm else None

        rec = {
            "session": sess_index,
            "step": step_no if is_step else 0,
            "is_step": is_step,
            "from": from_val,
            "to": to_val,
            "t0_ms": seg_t[0],
            "dur_ms": dur,
            "samples": len(seg_t),
            "mode_pct": mode_fractions(modes),
            "peak_pwm": peak_pwm,
            "series": {},
        }

        if have_avg:
            rec["series"]["avg"] = analyze_series(
                seg_t, session["avg"][a:b], from_val, to_val, deadband, last_n)
        for c in have_fingers:
            rec["series"][c] = analyze_series(
                seg_t, session[c][a:b], from_val, to_val, deadband, last_n)

        out.append(rec)

    return out


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _fmt(v: Optional[float], width: int, prec: int = 1, suffix: str = "") -> str:
    if v is None:
        return f"{'-':>{width}}"
    return f"{v:>{width}.{prec}f}{suffix}"


def print_records(records: List[dict], deadband: float) -> None:
    if not records:
        print("No data segments found.")
        return

    print(f"Per-finger flexion step-response  (deadband = +/-{deadband:.1f} deg)")
    print("All times in milliseconds. 'sse' = mean(last N) - target.\n")

    for rec in records:
        mp = rec["mode_pct"]
        tag = f"step #{rec['step']}" if rec["is_step"] else "initial (no commanded step)"
        peak = "-" if rec["peak_pwm"] is None else f"{int(rec['peak_pwm'])}"
        print(f"Session {rec['session']} | {tag}: "
              f"target {rec['from']:.0f} -> {rec['to']:.0f} deg  "
              f"(t0={int(rec['t0_ms'])} ms, dur={int(rec['dur_ms'])} ms, "
              f"P {mp['P']:.0f}% / V {mp['V']:.0f}% / H {mp['H']:.0f}%, "
              f"peak_pwm={peak})")

        hdr = (f"  {'series':<7}{'final':>8}{'sse':>8}{'t->band':>10}"
               f"{'rise10-90':>11}{'overshoot':>11}{'settling':>11}")
        print(hdr)
        for name in SERIES_ORDER:
            s = rec["series"].get(name)
            if s is None:
                continue
            print(f"  {name:<7}"
                  f"{_fmt(s['final'], 8)}"
                  f"{_fmt(s['sse'], 8, suffix='')}"
                  f"{_fmt(s['time_to_band_ms'], 10, 0)}"
                  f"{_fmt(s['rise_10_90_ms'], 11, 0)}"
                  f"{_fmt(s['overshoot_pct'], 11, 1)}"
                  f"{_fmt(s['settling_ms'], 11, 0)}")
        print()


def _round(v, prec: int = 3):
    """Round floats for tidy report output; leave ints/None/strings untouched."""
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, float):
        return round(v + 0.0, prec)  # +0.0 collapses -0.0 to 0.0
    return v


def _round_record(rec: dict) -> dict:
    out = {k: _round(v) for k, v in rec.items() if k not in ("mode_pct", "series")}
    out["mode_pct"] = {k: _round(v, 1) for k, v in rec["mode_pct"].items()}
    out["series"] = {
        name: {k: _round(v) for k, v in s.items()}
        for name, s in rec["series"].items()
    }
    return out


def export_json(records: List[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([_round_record(r) for r in records], fh, indent=2)


def export_csv(records: List[dict], path: str) -> None:
    cols = ["session", "step", "is_step", "from", "to", "t0_ms", "dur_ms",
            "mode_P_pct", "mode_V_pct", "mode_H_pct", "peak_pwm",
            "series", "samples", "final", "sse",
            "time_to_band_ms", "rise_10_90_ms", "overshoot_pct", "settling_ms"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csvmod.writer(fh)
        w.writerow(cols)
        for rec in records:
            mp = rec["mode_pct"]
            base = [rec["session"], rec["step"], int(rec["is_step"]),
                    _round(rec["from"]), _round(rec["to"]),
                    _round(rec["t0_ms"]), _round(rec["dur_ms"]),
                    round(mp["P"], 1), round(mp["V"], 1), round(mp["H"], 1),
                    rec["peak_pwm"]]
            for name in SERIES_ORDER:
                s = rec["series"].get(name)
                if s is None:
                    continue
                w.writerow(base + [name, s["samples"], _round(s["final"]),
                                   _round(s["sse"]), _round(s["time_to_band_ms"]),
                                   _round(s["rise_10_90_ms"]),
                                   _round(s["overshoot_pct"]),
                                   _round(s["settling_ms"])])


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #
def _selftest() -> int:
    # Idle at 0 deg, then a commanded step to 40 deg with a first-order rise and a
    # small overshoot. 100 ms grid. The step segment is what exercises rise/overshoot.
    import math
    t = [i * 100.0 for i in range(0, 31)]   # 0..3000 ms
    target = [0.0] * 10 + [40.0] * 21       # step at t = 1000 ms
    tau = 300.0
    t_step = 1000.0
    avg = []
    for i, tv in enumerate(t):
        if i < 10:
            avg.append(0.0)
            continue
        local = tv - t_step
        base = 40.0 * (1.0 - math.exp(-local / tau))
        overshoot = 1.5 * math.exp(-(local - 400.0) ** 2 / (2 * 150.0 ** 2))
        avg.append(base + overshoot)

    session = {"t_ms": t, "target": target, "avg": avg, "mode": ["P"] * len(t),
               "pump_pwm": [150.0] * len(t)}
    recs = analyze_session(session, 1, deadband=3.0, last_n=5, min_step=5.0)
    step_recs = [r for r in recs if r["is_step"]]

    ok = True
    if len(step_recs) != 1:
        ok = False
        print(f"SELFTEST FAIL: expected 1 step segment, got {len(step_recs)}")
    else:
        s = step_recs[0]["series"]["avg"]
        if s["time_to_band_ms"] is None or not (300 <= s["time_to_band_ms"] <= 1500):
            ok = False
            print(f"SELFTEST FAIL: time_to_band out of range: {s['time_to_band_ms']}")
        if s["sse"] is None or abs(s["sse"]) > 1.0:
            ok = False
            print(f"SELFTEST FAIL: |sse| too large: {s['sse']}")
        if s["rise_10_90_ms"] is None or s["rise_10_90_ms"] <= 0:
            ok = False
            print(f"SELFTEST FAIL: rise_10_90 invalid: {s['rise_10_90_ms']}")
        if s["overshoot_pct"] is None or not (0 <= s["overshoot_pct"] < 25):
            ok = False
            print(f"SELFTEST FAIL: overshoot_pct out of range: {s['overshoot_pct']}")

    # Two-step detection check.
    t2 = [i * 100.0 for i in range(0, 21)]
    target2 = [0.0] * 10 + [40.0] * 11
    avg2 = [0.0] * 10 + [40.0] * 11
    s2 = {"t_ms": t2, "target": target2, "avg": avg2,
          "mode": ["H"] * 21, "pump_pwm": [0.0] * 21}
    recs2 = analyze_session(s2, 1, 3.0, 5, 5.0)
    steps = [r for r in recs2 if r["is_step"]]
    if len(steps) != 1:
        ok = False
        print(f"SELFTEST FAIL: expected 1 commanded step, got {len(steps)}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Per-finger flexion step-response metrics from a glove CSV log.")
    p.add_argument("csv", nargs="?", help="path to the captured CSV/serial log")
    p.add_argument("--deadband", type=float, default=3.0,
                   help="target band in deg (default 3.0, matches firmware DEADBAND_DEG)")
    p.add_argument("--last-n", type=int, default=10,
                   help="samples averaged for steady-state error (default 10)")
    p.add_argument("--min-step", type=float, default=5.0,
                   help="minimum target change (deg) counted as a step (default 5.0)")
    p.add_argument("--json", help="write the full report to this JSON file")
    p.add_argument("--csv", dest="csv_out", help="write a flat per-series CSV report")
    p.add_argument("--quiet", action="store_true", help="suppress the stdout table")
    p.add_argument("--selftest", action="store_true", help="run built-in self-test and exit")
    args = p.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.csv:
        p.error("a CSV path is required (or use --selftest)")

    try:
        sessions = parse_log(args.csv)
    except OSError as exc:
        print(f"error: cannot read {args.csv}: {exc}", file=sys.stderr)
        return 2

    if not sessions:
        print("error: no usable data rows found "
              "(use validate_csv_schema.py to check the log)", file=sys.stderr)
        return 2

    records: List[dict] = []
    for idx, sess in enumerate(sessions, start=1):
        records.extend(analyze_session(
            sess, idx, args.deadband, args.last_n, args.min_step))

    if not args.quiet:
        print_records(records, args.deadband)
        print("Note: metrics describe the log source only; not hardware or "
              "clinical proof. See f*_closed columns for true valve timing.")

    if args.json:
        export_json(records, args.json)
        print(f"[json ] wrote {args.json}")
    if args.csv_out:
        export_csv(records, args.csv_out)
        print(f"[csv  ] wrote {args.csv_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
