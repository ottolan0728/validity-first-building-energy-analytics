"""Audit PLEIAData's analysis-ready hourly files without modifying raw data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


EXPECTED_MD5 = "f2deee82939dc05663078b2220639285"


def file_md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - compatibility with the repository checksum
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_summary(path: Path) -> dict[str, object]:
    first_line = path.open("r", encoding="utf-8-sig", errors="replace").readline()
    separator = ";" if first_line.count(";") > first_line.count(",") else ","
    frame = pd.read_csv(path, sep=separator)
    result: dict[str, object] = {
        "file": path.name,
        "separator": separator,
        "rows": len(frame),
        "columns": list(frame.columns),
        "missing_cells": int(frame.isna().sum().sum()),
    }
    date_column = next((c for c in frame.columns if "date" in c.lower()), None)
    if date_column:
        timestamps = pd.to_datetime(frame[date_column], errors="coerce", utc=True)
        start, end = timestamps.min(), timestamps.max()
        expected_hours = int((end - start).total_seconds() / 3600) + 1
        result.update(
            {
                "time_start": start.isoformat(),
                "time_end": end.isoformat(),
                "valid_timestamps": int(timestamps.notna().sum()),
                "unique_timestamps": int(timestamps.nunique()),
                "duplicate_timestamps": int(timestamps.duplicated().sum()),
                "expected_hours": expected_hours,
                "coverage_rate": float(timestamps.nunique() / expected_hours),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="Directory containing Data_Nature.zip")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    archive = args.root / "Data_Nature.zip"
    data_dir = args.root / "extracted" / "Data_Nature" / "data"
    patterns = [
        "cons*-60T.csv",
        "temp-sensor*-60T.csv",
        "hvac-agg*-60T.csv",
        "data-model-consumo*-60T.csv",
        "data-weather-60T.csv",
        "relations-*.csv",
    ]
    tables = []
    for pattern in patterns:
        tables.extend(table_summary(path) for path in sorted(data_dir.glob(pattern)))

    local_md5 = file_md5(archive)
    report = {
        "archive": str(archive.resolve()),
        "archive_bytes": archive.stat().st_size,
        "md5": local_md5,
        "expected_md5": EXPECTED_MD5,
        "checksum_pass": local_md5 == EXPECTED_MD5,
        "tables": tables,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report["checksum_pass"]:
        raise SystemExit("Archive checksum mismatch")


if __name__ == "__main__":
    main()

