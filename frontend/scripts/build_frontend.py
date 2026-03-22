"""Build the static dashboard into frontend/build for local serving."""

from __future__ import annotations

import shutil
from pathlib import Path


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = FRONTEND_ROOT / "public"
BUILD_DIR = FRONTEND_ROOT / "build"


def main() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    shutil.copytree(PUBLIC_DIR, BUILD_DIR)
    print(f"Built frontend to {BUILD_DIR}")


if __name__ == "__main__":
    main()
