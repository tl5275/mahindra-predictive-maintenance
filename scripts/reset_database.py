"""Reset generated data artifacts used by simulation runs."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIRS = [
    PROJECT_ROOT / "data" / "processed_data",
    PROJECT_ROOT / "data" / "raw_telemetry",
    PROJECT_ROOT / "data" / "fleet_logs",
]


def main() -> None:
    deleted_count = 0
    for directory in DATA_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
        for file_path in directory.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                deleted_count += 1
    print(f"Reset complete. Deleted {deleted_count} generated files.")


if __name__ == "__main__":
    main()
