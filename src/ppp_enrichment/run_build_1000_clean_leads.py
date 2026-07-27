"""Build a deduped, keyword-filtered batch of 1000 clean leads from output CSVs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import config
from .run_export_clean import _drop_blocked_industry_leads

_REQUIRED_COLS = [
    "First Name",
    "Second Name",
    "Email Address",
    "Phone Number",
    "Company Name",
    "Company URL",
]


def _list_clean_lead_files(output_dir: Path) -> list[Path]:
    files = sorted(output_dir.glob("clean_leads_*.csv"), key=lambda p: p.name, reverse=True)
    return files


def _load_all_clean_leads(files: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in files:
        try:
            df = pd.read_csv(path, dtype="string")
        except Exception as exc:  # noqa: BLE001 — skip corrupt/partial CI artifacts
            print(f"Skipping unreadable file {path.name}: {exc}")
            continue
        missing = [c for c in _REQUIRED_COLS if c not in df.columns]
        if missing:
            print(f"Skipping {path.name}: missing columns {missing}")
            continue
        frames.append(df[_REQUIRED_COLS].copy())
    if not frames:
        return pd.DataFrame(columns=_REQUIRED_COLS)
    return pd.concat(frames, ignore_index=True)


def build_1000_clean_leads(
    *,
    output_dir: Path | None = None,
    target: int | None = None,
    out_path: Path | None = None,
) -> Path:
    """Aggregate clean_leads_*.csv → filtered, deduped target-size CSV."""
    src_dir = output_dir or config.OUTPUT_DIR
    n_target = target if target is not None else config.CLEAN_1000_TARGET
    dest_dir = config.CLEAN_1000_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = out_path or (dest_dir / config.CLEAN_1000_FILENAME)

    files = _list_clean_lead_files(src_dir)
    print(f"Source clean_leads files: {len(files)}")
    combined = _load_all_clean_leads(files)
    loaded = len(combined)
    print(f"Rows loaded (pre-filter): {loaded}")

    if combined.empty:
        empty = pd.DataFrame(columns=_REQUIRED_COLS)
        empty.to_csv(dest, index=False, encoding=config.CSV_WRITE_ENCODING)
        print(f"Wrote empty file (no source rows): {dest}")
        return dest

    for col in _REQUIRED_COLS:
        combined[col] = combined[col].astype("string").str.strip()
    combined["Email Address"] = combined["Email Address"].str.lower()
    combined["First Name"] = combined["First Name"].str.title()
    combined["Second Name"] = combined["Second Name"].str.title()

    before_dedup = len(combined)
    combined = combined.drop_duplicates(
        subset=["Company Name", "Email Address", "Phone Number"],
        keep="first",
    )
    dropped_dupes = before_dedup - len(combined)

    combined, dropped_industry = _drop_blocked_industry_leads(combined)

    if len(combined) > n_target:
        combined = combined.iloc[:n_target].copy()

    combined.to_csv(dest, index=False, encoding=config.CSV_WRITE_ENCODING)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    dated = dest_dir / f"1000_clean_leads_{stamp}.csv"
    combined.to_csv(dated, index=False, encoding=config.CSV_WRITE_ENCODING)

    print(f"Duplicate rows removed: {dropped_dupes}")
    print(f"Rows dropped due to industry keywords: {dropped_industry}")
    print(f"Final lead count: {len(combined)} (target {n_target})")
    print(f"Wrote: {dest}")
    print(f"Wrote: {dated}")
    if len(combined) < n_target:
        print(
            f"Warning: only {len(combined)} leads available after filters "
            f"(need {n_target})."
        )
    return dest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build 1000 deduped keyword-filtered clean leads from output CSVs.",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=config.CLEAN_1000_TARGET,
        help=f"Number of leads to keep (default: {config.CLEAN_1000_TARGET}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory containing clean_leads_*.csv (default: data/output).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    build_1000_clean_leads(output_dir=args.output_dir, target=args.target)


if __name__ == "__main__":
    main()
