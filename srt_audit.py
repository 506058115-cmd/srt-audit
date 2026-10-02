#!/usr/bin/env python3
"""Check SubRip cue structure and timing without printing subtitle text."""

import argparse
from dataclasses import dataclass
import re
import sys
from pathlib import Path


MAX_BYTES = 32 * 1024 * 1024
INDEX = re.compile(r"\d{1,9}")
TIMESTAMP = re.compile(
    r"^\s*(\d{2,9}):(\d{2}):(\d{2}),(\d{3})[ \t]+-->[ \t]+"
    r"(\d{2,9}):(\d{2}):(\d{2}),(\d{3})(?:[ \t]+.*)?[ \t]*$"
)


@dataclass(frozen=True)
class Cue:
    number: int | None
    line: int
    start: int
    end: int


def milliseconds(hours, minutes, seconds, millis):
    hours, minutes, seconds, millis = map(int, (hours, minutes, seconds, millis))
    if minutes > 59 or seconds > 59:
        raise ValueError
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def inspect(content):
    issues = []
    cues = []
    lines = content.splitlines()
    cursor = 0

    while cursor < len(lines):
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        if cursor == len(lines):
            break

        first = cursor
        while cursor < len(lines) and lines[cursor].strip():
            cursor += 1
        block = lines[first:cursor]
        number = None
        time_offset = 0
        if INDEX.fullmatch(block[0].strip()):
            number = int(block[0].strip())
            time_offset = 1

        time_line = first + time_offset + 1
        if time_offset >= len(block):
            issues.append((time_line, "error", "missing timestamp"))
            continue
        match = TIMESTAMP.fullmatch(block[time_offset])
        if not match:
            issues.append((time_line, "error", "malformed or missing timestamp"))
            continue
        try:
            start = milliseconds(*match.groups()[:4])
            end = milliseconds(*match.groups()[4:])
        except ValueError:
            issues.append((time_line, "error", "minutes and seconds must be 00–59"))
            continue
        if start >= end:
            message = "cue must end after it starts" if start > end else "zero-length cue"
            severity = "error" if start > end else "warning"
            issues.append((time_line, severity, message))
            if start > end:
                continue
        if not any(line.strip() for line in block[time_offset + 1 :]):
            issues.append((time_line, "warning", "cue has no subtitle text"))
        cues.append(Cue(number, time_line, start, end))

    seen_numbers = set()
    previous_start = None
    for cue in cues:
        if cue.number is not None:
            if cue.number in seen_numbers:
                issues.append((cue.line, "warning", "duplicate cue number"))
            seen_numbers.add(cue.number)
        if previous_start is not None and cue.start < previous_start:
            issues.append((cue.line, "warning", "cue starts are out of order"))
        previous_start = cue.start

    latest_end = -1
    for cue in sorted(cues, key=lambda item: (item.start, item.end)):
        if cue.start < latest_end:
            issues.append((cue.line, "warning", "cue overlaps another cue"))
        latest_end = max(latest_end, cue.end)

    return cues, sorted(issues, key=lambda issue: (issue[0], issue[1]))


def read_input(name):
    if name == "-":
        data = sys.stdin.buffer.read(MAX_BYTES + 1)
    else:
        with Path(name).open("rb") as source:
            data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("input exceeds the 32 MiB limit")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("input is not valid UTF-8") from error


def main():
    parser = argparse.ArgumentParser(
        description="Check SubRip structure and cue timing without showing subtitle text."
    )
    parser.add_argument("input", help="SRT file, or - to read standard input")
    args = parser.parse_args()

    try:
        content = read_input(args.input)
    except ValueError as error:
        print(f"srt-audit: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        reason = error.strerror or "unable to read input"
        print(f"srt-audit: {reason}", file=sys.stderr)
        return 2

    cues, issues = inspect(content)
    errors = sum(severity == "error" for _, severity, _ in issues)
    warnings = len(issues) - errors
    print(f"{len(cues)} cue(s): {errors} error(s), {warnings} warning(s)")
    for line, severity, message in issues:
        print(f"line {line}: {severity}: {message}")
    if not cues and not errors:
        print("No SubRip cue timestamps found.")
        return 1
    if not issues:
        print("No structural or timing issues found.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
