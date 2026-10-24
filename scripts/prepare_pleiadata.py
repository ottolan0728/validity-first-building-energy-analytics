"""CLI for producing the analysis-ready PLEIAData table."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.data import prepare_dataset, write_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--history", type=int, choices=[24, 168], default=168)
    args = parser.parse_args()
    frame = prepare_dataset(args.data_dir, horizon=args.horizon, history=args.history)
    manifest = write_dataset(frame, args.output, args.data_dir)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
