#!/usr/bin/env python3
"""
validate_csv_schema.py - Verify a captured CSV log against the firmware's CSV contract.

Target firmware : VAA0.0.5.x_Mega2560 (minimal proportional controller line)
Pairs with      : any raw serial capture of the firmware's 25-column CSV schema
                  (see samples/sample_serial_log.csv in this repository)
Validation level : host-side L1 offline check. Does NOT touch firmware, actuation,
                   safety, control, or the logging schema. Read-only on the .ino.
Dependencies     : Python 3.8+ standard library only (no pip, CI-friendly).

WHY THIS EXISTS
  The firmware is the single source of truth for the CSV schema. printCSVHeader()
  in the .ino emits exactly 25 columns:

    t_ms,target,kp_pressure,kp_vacuum,f1,f2,f3,f4,f5,avg,error,mode,pump_pwm,
    central_pressure,f1_closed,f2_closed,f3_closed,f4_closed,f5_closed,
    ax,ay,az,gx,gy,gz

  This tool catches drift between a captured log and that contract (wrong column
  count, renamed/reordered columns, corrupt rows, illegal values) so downstream
  analysis and report numbers are never computed on a malformed log.

SCHEMA SOURCE (priority order)
  1. --header "col1,col2,..."      explicit header string
  2. --ino path/to/Controller.ino  expected header read live from printCSVHeader()
  3. (none)                        internal-consistency mode: no header-equality
                                   check, but field counts and per-column types are
                                   still validated against the log's own header.

  Mode 2 keeps the .ino as the literal authority: point it at the firmware you
  actually flashed and the expected header is whatever that build prints.

PARSING RULES (match the firmware's serial output)
  * Lines starting with '#' are firmware diagnostics  -> ignored.
  * Blank lines                                       -> ignored.
  * A line whose first field is 't_ms' is a header row. The firmware reprints it
    on reset, so multiple header rows simply mark multiple logging sessions.
  * Each data row is validated against the header that precedes it.

PER-COLUMN TYPE RULES (keyed by column NAME, so extra columns degrade gracefully)
  t_ms                          -> integer >= 0
  mode                          -> one of P / V / H
  pump_pwm                      -> integer 0..255
  central_pressure, *_closed    -> integer in {0, 1}
  every other known column      -> float
  unknown column                -> warning; float-parse attempted (--strict fails)

EXIT CODES
  0 = pass    1 = validation failure    2 = usage / I/O error

USAGE
  python tools/validate_csv_schema.py samples/sample_serial_log.csv
  python tools/validate_csv_schema.py log.csv --ino path/to/YourController.ino
  python tools/validate_csv_schema.py log.csv --header "t_ms,target,...,gz" --strict
  python tools/validate_csv_schema.py --selftest
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import List, Optional, Tuple

# Reference contract for VAA0.0.5.x. Used by --selftest and for messages only;
# it is NOT auto-applied to a user's log unless they pass --ino or --header.
REFERENCE_HEADER: List[str] = [
    "t_ms", "target", "kp_pressure", "kp_vacuum",
    "f1", "f2", "f3", "f4", "f5",
    "avg", "error", "mode", "pump_pwm", "central_pressure",
    "f1_closed", "f2_closed", "f3_closed", "f4_closed", "f5_closed",
    "ax", "ay", "az", "gx", "gy", "gz",
]

MODE_VALUES = ("P", "V", "H")
MAX_REPORTED = 25  # cap printed errors/warnings; full counts are always reported


# --------------------------------------------------------------------------- #
# Schema-source helpers
# --------------------------------------------------------------------------- #
def extract_header_from_ino(path: str) -> List[str]:
    """Read the expected CSV header straight out of printCSVHeader() in a .ino."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    # Prefer the body of printCSVHeader(); fall back to the whole file.
    region = text
    m = re.search(r"printCSVHeader\s*\([^)]*\)\s*\{(.*?)\}", text, re.DOTALL)
    if m:
        region = m.group(1)

    fm = re.search(r'F\(\s*"([^"]*\bt_ms\b[^"]*)"\s*\)', region)
    if fm is None:
        fm = re.search(r'"([^"]*\bt_ms\b[^"]*,[^"]*)"', region)
    if fm is None:
        raise ValueError(
            f"could not find a CSV header string in printCSVHeader() of {path}"
        )
    return [c.strip() for c in fm.group(1).split(",")]


def parse_header_arg(s: str) -> List[str]:
    return [c.strip() for c in s.split(",") if c.strip() != ""]


# --------------------------------------------------------------------------- #
# Per-column typing (by name)
# --------------------------------------------------------------------------- #
_FLOAT_COLS = {
    "target", "kp_pressure", "kp_vacuum", "avg", "error",
    "f1", "f2", "f3", "f4", "f5",
    "ax", "ay", "az", "gx", "gy", "gz",
}


def column_kind(name: str) -> str:
    if name == "t_ms":
        return "uint"
    if name == "mode":
        return "mode"
    if name == "pump_pwm":
        return "pwm"
    if name == "central_pressure" or name.endswith("_closed"):
        return "bool01"
    if name in _FLOAT_COLS:
        return "float"
    return "unknown"


def check_value(name: str, value: str) -> Optional[str]:
    """Return an error string if the value violates its column type, else None."""
    kind = column_kind(name)
    v = value.strip()

    if kind in ("uint", "pwm", "bool01"):
        try:
            iv = int(v)
        except ValueError:
            return f"{name}='{value}' is not an integer"
        if kind == "uint" and iv < 0:
            return f"{name}={iv} is negative"
        if kind == "pwm" and not (0 <= iv <= 255):
            return f"{name}={iv} out of PWM range 0..255"
        if kind == "bool01" and iv not in (0, 1):
            return f"{name}={iv} is not 0 or 1"
        return None

    if kind == "mode":
        if v not in MODE_VALUES:
            return f"mode='{value}' not one of P/V/H"
        return None

    # float and unknown both attempt a float parse
    try:
        float(v)
    except ValueError:
        return f"{name}='{value}' is not a number"
    return None


# --------------------------------------------------------------------------- #
# Core validation
# --------------------------------------------------------------------------- #
class Report:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.sessions = 0
        self.data_rows = 0
        self.header_rows = 0
        self.unknown_cols: set = set()

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_lines(
    lines: List[str],
    expected: Optional[List[str]],
    strict: bool,
) -> Report:
    rep = Report()
    cur_header: Optional[List[str]] = None
    cur_ncol = 0
    first_header: Optional[List[str]] = None
    last_t: Optional[int] = None

    for lineno, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue

        fields = [f.strip() for f in line.split(",")]

        # Header row?
        if fields and fields[0] == "t_ms":
            rep.header_rows += 1
            rep.sessions += 1
            cur_header = fields
            cur_ncol = len(fields)
            last_t = None

            if first_header is None:
                first_header = fields

            ref = expected if expected is not None else first_header
            if ref is not None and fields != ref:
                where = "expected schema" if expected is not None else "first header"
                rep.err(f"line {lineno}: header differs from {where}\n"
                        f"    got : {','.join(fields)}\n"
                        f"    want: {','.join(ref)}")

            # Note unknown columns once.
            for name in fields:
                if column_kind(name) == "unknown" and name not in rep.unknown_cols:
                    rep.unknown_cols.add(name)
                    rep.warn(f"line {lineno}: unknown column '{name}' "
                             f"(field-count + float-parse only)")
            continue

        # Data row.
        header = cur_header if cur_header is not None else expected
        ncol = cur_ncol if cur_header is not None else (len(expected) if expected else 0)
        if header is None:
            rep.err(f"line {lineno}: data row before any header "
                    f"(provide --ino/--header to validate this log)")
            rep.data_rows += 1
            continue

        rep.data_rows += 1

        if len(fields) != ncol:
            rep.err(f"line {lineno}: has {len(fields)} fields, header has {ncol}")
            continue

        for name, val in zip(header, fields):
            msg = check_value(name, val)
            if msg is not None:
                rep.err(f"line {lineno}: {msg}")

        # Soft monotonic-time check within a session.
        try:
            t = int(fields[0])
            if last_t is not None and t < last_t:
                rep.warn(f"line {lineno}: t_ms went backward "
                         f"({last_t} -> {t}); possible reset without header")
            last_t = t
        except ValueError:
            pass  # already flagged by check_value

    if strict and rep.warnings:
        # Promote: warnings now count toward failure (handled by caller via count).
        pass

    return rep


def print_report(rep: Report, path: str, source_desc: str, strict: bool) -> int:
    print(f"file            : {path}")
    print(f"schema source   : {source_desc}")
    print(f"sessions        : {rep.sessions}")
    print(f"data rows       : {rep.data_rows}")
    if rep.unknown_cols:
        print(f"unknown columns : {', '.join(sorted(rep.unknown_cols))}")

    if rep.warnings:
        print(f"\nwarnings ({len(rep.warnings)}):")
        for w in rep.warnings[:MAX_REPORTED]:
            print(f"  - {w}")
        if len(rep.warnings) > MAX_REPORTED:
            print(f"  ... and {len(rep.warnings) - MAX_REPORTED} more")

    if rep.errors:
        print(f"\nerrors ({len(rep.errors)}):")
        for e in rep.errors[:MAX_REPORTED]:
            print(f"  - {e}")
        if len(rep.errors) > MAX_REPORTED:
            print(f"  ... and {len(rep.errors) - MAX_REPORTED} more")

    failed = bool(rep.errors) or (strict and bool(rep.warnings))
    print("\nRESULT          : " + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #
def _selftest() -> int:
    hdr = ",".join(REFERENCE_HEADER)
    good = "\n".join([
        "# diagnostic line, ignored",
        hdr,
        "100,40.0,10.00,3.50,28.2,28.0,27.8,27.5,27.4,27.8,12.2,H,0,0,0,0,0,0,0,0.000,0.000,0.000,0.00,0.00,0.00",
        "200,40.0,10.00,3.50,30.0,30.0,30.0,30.0,30.0,30.0,10.0,P,150,1,0,0,0,0,0,0.000,0.000,1.000,0.00,0.00,0.00",
        "# board reset below",
        hdr,
        "5,40.0,10.00,3.50,0.0,0.0,0.0,0.0,0.0,0.0,40.0,V,80,0,0,0,0,0,0,0.000,0.000,0.000,0.00,0.00,0.00",
    ]).splitlines()

    bad = "\n".join([
        hdr,
        "100,40.0,10.00,3.50,28.2,28.0,27.8,27.5,27.4,27.8,12.2,H,0,0,0,0,0,0,0,0.000,0.000,0.000,0.00,0.00",   # 24 fields
        "200,40.0,10.00,3.50,30.0,30.0,30.0,30.0,30.0,30.0,10.0,X,300,2,0,0,0,0,0,0.0,0.0,0.0,0.0,0.0,0.0",       # bad mode/pwm/bool
    ]).splitlines()

    r_good = validate_lines(good, REFERENCE_HEADER, strict=False)
    r_bad = validate_lines(bad, REFERENCE_HEADER, strict=False)

    ok = True
    if r_good.errors:
        ok = False
        print("SELFTEST FAIL: clean log produced errors:", r_good.errors)
    if r_good.sessions != 2:
        ok = False
        print(f"SELFTEST FAIL: expected 2 sessions, got {r_good.sessions}")
    if not r_bad.errors:
        ok = False
        print("SELFTEST FAIL: malformed log produced no errors")
    else:
        # Expect: field-count error + invalid mode + pwm range + bool range.
        joined = " | ".join(r_bad.errors)
        for needle in ("fields", "mode=", "PWM range", "not 0 or 1"):
            if needle not in joined:
                ok = False
                print(f"SELFTEST FAIL: expected an error containing '{needle}'")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Validate a Soft Robotic Glove CSV log against the firmware schema.",
    )
    p.add_argument("csv", nargs="?", help="path to the captured CSV/serial log")
    p.add_argument("--ino", help="path to a .ino; expected header read from printCSVHeader()")
    p.add_argument("--header", help='explicit expected header, e.g. "t_ms,target,...,gz"')
    p.add_argument("--strict", action="store_true",
                   help="treat warnings (e.g. unknown columns) as failure")
    p.add_argument("--selftest", action="store_true", help="run built-in self-test and exit")
    args = p.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not args.csv:
        p.error("a CSV path is required (or use --selftest)")

    # Resolve expected header.
    expected: Optional[List[str]] = None
    source_desc = "internal consistency only (no --ino/--header)"
    try:
        if args.header:
            expected = parse_header_arg(args.header)
            source_desc = "--header argument"
        elif args.ino:
            expected = extract_header_from_ino(args.ino)
            source_desc = f"printCSVHeader() in {args.ino}"
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        with open(args.csv, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"error: cannot read {args.csv}: {exc}", file=sys.stderr)
        return 2

    rep = validate_lines(lines, expected, strict=args.strict)
    return print_report(rep, args.csv, source_desc, args.strict)


if __name__ == "__main__":
    sys.exit(main())
