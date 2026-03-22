"""Launcher for the production-style Docker Compose platform."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
FRONTEND_URL = "http://localhost:8080"
BACKEND_HEALTH_URL = "http://localhost:8000/health"


def _compose_base() -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE)]


def _run(command: list[str], check: bool = True) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=check)


def _wait_for_http(url: str, timeout_seconds: float = 180.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                if response.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2)
    return False


def command_up(args: argparse.Namespace) -> None:
    command = _compose_base() + ["up"]
    if not args.skip_build:
        command.append("--build")
    if not args.attach:
        command.append("-d")

    _run(command)

    if args.attach:
        return

    backend_ready = _wait_for_http(BACKEND_HEALTH_URL)
    frontend_ready = _wait_for_http(FRONTEND_URL)

    if backend_ready:
        print(f"Backend ready at {BACKEND_HEALTH_URL}")
    if frontend_ready:
        print(f"Frontend ready at {FRONTEND_URL}")
        if not args.no_browser:
            try:
                webbrowser.open(FRONTEND_URL)
            except Exception:
                pass


def command_down(_: argparse.Namespace) -> None:
    _run(_compose_base() + ["down", "--volumes"])


def command_logs(args: argparse.Namespace) -> None:
    command = _compose_base() + ["logs", "-f"]
    if args.service:
        command.append(args.service)
    _run(command, check=False)


def command_ps(_: argparse.Namespace) -> None:
    _run(_compose_base() + ["ps"], check=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the Mahindra predictive maintenance platform.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    up_parser = subparsers.add_parser("up", help="Build and start the full platform stack.")
    up_parser.add_argument("--attach", action="store_true", help="Stream compose logs instead of detaching.")
    up_parser.add_argument("--skip-build", action="store_true", help="Reuse existing images.")
    up_parser.add_argument("--no-browser", action="store_true", help="Do not open the dashboard after startup.")
    up_parser.set_defaults(handler=command_up)

    down_parser = subparsers.add_parser("down", help="Stop the platform stack and remove volumes.")
    down_parser.set_defaults(handler=command_down)

    logs_parser = subparsers.add_parser("logs", help="Tail compose logs.")
    logs_parser.add_argument("service", nargs="?", help="Optional service name to filter logs.")
    logs_parser.set_defaults(handler=command_logs)

    ps_parser = subparsers.add_parser("ps", help="Show compose service status.")
    ps_parser.set_defaults(handler=command_ps)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
